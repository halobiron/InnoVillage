"""Read product detail hrefs from the category pages referenced by the snapshot."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "data" / "coopsmile_catalog.json"
MANUAL_MATCHES = {
    # These snapshot names differ from the live collection only by punctuation
    # or a descriptive qualifier; href and displayed product title were checked.
    "CS-HOME-001": "https://coopsmile.vn/products/nuoc-xa-mem-vai-dam-dac-comfort-hoa-trang-tinh-khoi-tui-3-6l",
    "CS-HOME-012": "https://coopsmile.vn/products/nuoc-lau-san-sunlight-huong-hoa-ha-bac-ha-t3-6kg",
    "CS-HOME-019": "https://coopsmile.vn/products/nuoc-lau-san-coop-select-lily-huong-hoa-tui-3-2l",
}


def normalize(value: str) -> str:
    folded = unicodedata.normalize("NFD", value.casefold())
    folded = "".join(c for c in folded if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


class ProductAnchors(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[tuple[str, str]] = []
        self.href: str | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a":
            self.href = attributes.get("href")
            self.text = [attributes.get("title") or ""]
        elif self.href and tag == "img":
            self.text.extend([attributes.get("alt") or "", attributes.get("title") or ""])

    def handle_data(self, data: str) -> None:
        if self.href:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.href:
            self.items.append((self.href, " ".join(self.text)))
            self.href = None
            self.text = []


def main() -> None:
    write = "--write" in sys.argv[1:]
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    categories = {item["url"] for item in catalog["products"]}
    anchors: list[tuple[str, str]] = []
    for category_url in sorted(categories):
        for page in range(1, 5):
            page_url = category_url if page == 1 else f"{category_url}?page={page}"
            response = requests.get(page_url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; product-link-audit/1.0)"
            }, timeout=30)
            response.raise_for_status()
            parser = ProductAnchors()
            parser.feed(response.text)
            page_anchors = [(urljoin(page_url, href), text) for href, text in parser.items
                            if href and "/products/" in href]
            anchors.extend(page_anchors)
            if page > 1 and not page_anchors:
                break

    found: dict[str, str] = {}
    for item in catalog["products"]:
        target = normalize(item["name"])
        ranked_by_url: dict[str, tuple[float, str, str]] = {}
        for href, text in anchors:
            candidate = normalize(text)
            # Exact containment is preferred. Fuzzy matching is only reported,
            # never used to overwrite source data without human review.
            score = 1.0 if target and target in candidate else SequenceMatcher(None, target, candidate).ratio()
            if score >= 0.40:
                prior = ranked_by_url.get(href)
                if prior is None or score > prior[0]:
                    ranked_by_url[href] = (score, href, text.strip())
        ranked = list(ranked_by_url.values())
        ranked.sort(reverse=True)
        best = ranked[0] if ranked else None
        if item["sku"] in MANUAL_MATCHES:
            href = MANUAL_MATCHES[item["sku"]]
            if any(candidate_href == href for candidate_href, _ in anchors):
                found[item["sku"]] = href
                print(f"MATCH\t{item['sku']}\t{href}\tmanual title confirmation")
            else:
                print(f"MISSING\t{item['sku']}\tmanual URL not found on category page")
        elif best and best[0] == 1.0 and target in normalize(best[2]):
            found[item["sku"]] = best[1]
            print(f"MATCH\t{item['sku']}\t{best[1]}\t{best[2]}")
        else:
            print(f"REVIEW\t{item['sku']}\t{item['name']}\t"
                  f"{best[0]:.3f} {best[1]} {best[2]}" if best else
                  f"MISSING\t{item['sku']}\t{item['name']}")

    if write:
        if len(found) != len(catalog["products"]):
            raise SystemExit(f"Refusing to write: matched {len(found)}/{len(catalog['products'])} products")
        raw = CATALOG.read_text(encoding="utf-8")
        for sku, href in found.items():
            pattern = re.compile(rf'(?m)^(\s*\{{"sku":"{re.escape(sku)}".*?)(\}}[,]?)$')
            match = pattern.search(raw)
            if not match:
                raise SystemExit(f"Could not safely locate snapshot row {sku}")
            row = match.group(1)
            if '"product_url":' in row:
                row = re.sub(r'"product_url":"[^"]*"',
                             '"product_url":' + json.dumps(href), row)
            else:
                row += ',"product_url":' + json.dumps(href)
            raw = raw[:match.start()] + row + match.group(2) + raw[match.end():]
        CATALOG.write_text(raw, encoding="utf-8")
        print(f"Updated {len(found)} product detail URLs in {CATALOG}")


if __name__ == "__main__":
    main()
