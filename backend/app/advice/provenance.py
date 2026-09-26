from __future__ import annotations
from app.schemas import FactCard


def format_vnd(n: int) -> str:
    return f"{n:,}".replace(",", ".") + "đ"


def facts_for_llm(cards: list[FactCard]) -> str:
    blocks = []
    for c in cards:
        rows = [f"  - {l.label}: {l.value}  [nguồn: {l.source}]" for l in c.lines]
        miss = ", ".join(c.missing)
        blocks.append(c.title + "\n" + "\n".join(rows) + f"\n  - CHƯA CÓ DỮ LIỆU: {miss}")
    return "\n\n".join(blocks)
