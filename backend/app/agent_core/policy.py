"""Tri thức chính sách cửa hàng (giờ mở cửa, đặt hàng, thanh toán, bảo hành, khiếu nại).

Nguồn: các file markdown đã biên tập trong app/data/policies/, mỗi mục `## ` là một chunk.
Retrieval nhẹ in-memory (token overlap trên chữ bỏ dấu); LLM soạn câu trả lời nhưng
mọi con số phải truy nguyên được về tài liệu — vi phạm thì trả nguyên văn chunk (fail-closed).
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent_core.text import strip_accents

log = logging.getLogger("agent_core")

_POLICY_DIR = Path(__file__).resolve().parents[1] / "data" / "policies"

# Bỏ các từ hội thoại không mang nghĩa retrieval.
_STOPWORDS = {
    "a", "ai", "anh", "ban", "ben", "chi", "cho", "co", "con", "cua", "da",
    "do", "duoc", "em", "gi", "hoi", "khong", "kia", "la", "minh", "nao",
    "nay", "nhe", "nhi", "nhu", "oi", "phai", "sao", "the", "thi", "toi",
    "vi", "voi", "vay",
}

def _system_prompt(addr: str, self_term: str) -> str:
    del addr, self_term
    return (
        "Bạn là nhân viên chăm sóc khách hàng của Co.opSmile. NGUYÊN TẮC:\n"
        "1. CHỈ trả lời dựa trên TÀI LIỆU được cung cấp. TUYỆT ĐỐI không bịa thông tin, "
        "không suy diễn chính sách không có trong tài liệu.\n"
        "2. Mọi con số (giờ giấc, số điện thoại, số ngày, số lượng) phải viết Y HỆT như trong tài liệu.\n"
        "3. Nếu tài liệu không có thông tin khách hỏi, nói thật là chưa có dữ liệu; không tự đoán số tổng đài, "
        "địa chỉ hoặc chính sách.\n"
        "4. Trả lời ngắn gọn 2-4 câu, giọng lễ phép 'Dạ/ạ', đi thẳng vào ý khách hỏi.\n"
        "4b. Nếu khách hỏi về một nhóm sản phẩm cụ thể, chỉ dùng tài liệu áp dụng cho nhóm đó.\n"
        "5. Kết thúc bằng một câu mời khách tiếp tục cho biết nhu cầu mua sắm nếu cần.\n"
        "5b. Chỉ dùng cách xưng hô khi khách đã thể hiện rõ trong hội thoại. Nếu không chắc, viết trung tính, "
        "không tự gán tuổi, giới tính hay vai vế.\n"
        "6. KHÔNG dùng định dạng Markdown (không dấu sao hay thăng); danh sách thì xuống dòng dùng dấu '-'."
    )


def _flat(text: str) -> str:
    lowered = text.lower()
    # Bỏ từ hỏi trước khi strip dấu để tránh chúng làm nhiễu token truy xuất.
    lowered = re.sub(r"\bmấy\b", " ", lowered)
    flat = strip_accents(lowered)
    # Chuẩn hóa cách viết tách âm tiết phổ biến để không còn token rác "ti", "vi".
    return re.sub(r"\bti\s+vi\b", "tivi", flat)


def _tokens(text: str) -> List[str]:
    return [
        t for t in re.split(r"[^\w]+", _flat(text))
        if len(t) > 1 and t not in _STOPWORDS
    ]


@lru_cache(maxsize=4)
def load_policy_chunks(policy_dir: Optional[str] = None) -> tuple:
    """Đọc mọi file .md trong thư mục chính sách, cắt chunk theo heading `## `."""
    base = Path(policy_dir) if policy_dir else _POLICY_DIR
    if not base.exists():
        log.warning("policy: thư mục tài liệu không tồn tại: %s", base)
        return tuple()
    chunks: List[Dict[str, Any]] = []
    for f in sorted(base.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("policy: không đọc được %s (%s)", f, e)
            continue
        for part in re.split(r"(?m)^##\s+", text)[1:]:
            title, _, body = part.partition("\n")
            body = body.strip()
            if body:
                chunks.append({"source": f.stem, "title": title.strip(), "text": body})
    log.info("policy: nạp %d chunk từ %s", len(chunks), base)
    return tuple(chunks)


def search_policy(query: str, top_k: int = 3, policy_dir: Optional[str] = None,
                  category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Chấm điểm chunk theo độ trùng token bỏ dấu (tiêu đề nhân đôi trọng số).
    category (nhóm hàng khách đang bàn) được trộn vào truy vấn để chunk nhắc tới
    nhóm đó thắng chunk chung chung."""
    chunks = load_policy_chunks(policy_dir)
    q_tokens = set(_tokens(f"{query} {category or ''}"))
    if not chunks or not q_tokens:
        return []
    scored = []
    category_flat = _flat(category).strip() if category else ""
    for c in chunks:
        title_tokens = set(_tokens(c["title"]))
        body_tokens = set(_tokens(c["text"]))
        score = 2.0 * len(q_tokens & title_tokens) + 1.0 * len(q_tokens & body_tokens)
        if category_flat and category_flat in _flat(f"{c['title']} {c['text']}"):
            # Khớp chính xác danh mục phải được ưu tiên hơn trùng lặp token chung.
            score += 20.0
        # Một token chỉ trùng trong thân bài là quá yếu; ít nhất phải trùng tiêu
        # đề (2 điểm), hai token thân bài, hoặc exact category (boost ở trên).
        if score >= 2.0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def _numbers_grounded(reply: str, docs: str) -> bool:
    """Mọi cụm số trong câu trả lời phải xuất hiện (theo dạng chỉ-chữ-số) trong tài liệu."""
    doc_nums = {re.sub(r"\D", "", m) for m in re.findall(r"\d[\d\.\,:h\-]*\d|\d", docs)}
    for m in re.findall(r"\d[\d\.\,:h\-]*\d|\d", reply):
        digits = re.sub(r"\D", "", m)
        if len(digits) <= 1:
            continue  # số đơn lẻ (đánh số danh sách) không coi là dữ kiện
        if digits not in doc_nums:
            log.warning("policy: câu trả lời chứa số lạ %r không có trong tài liệu", m)
            return False
    return True


def answer_policy(query: str, llm=None, policy_dir: Optional[str] = None,
                  history: Optional[List[Dict[str, str]]] = None,
                  category: Optional[str] = None, addr: str = "",
                  self_term: str = "") -> str:
    """Soạn câu trả lời chính sách THEO NGỮ CẢNH hội thoại (nhóm hàng khách đang bàn).
    LLM lỗi/bịa số -> trả nguyên văn chunk khớp nhất."""
    retrieval_query = query
    # Router chỉ gọi node này sau khi intent đã xác nhận câu hỏi policy. Với
    # Follow-up ngắn mượn câu hỏi gần nhất để giữ chủ đề sản phẩm.
    if category:
        for message in reversed(history or []):
            if message.get("role") == "user" and message.get("content"):
                retrieval_query = f"{message['content']} {query}"
                break
    hits = search_policy(retrieval_query, top_k=3, policy_dir=policy_dir, category=category)
    if not hits:
        log.info("policy: không tìm thấy chunk khớp cho %r", query)
        return ("Hiện mình chưa có thông tin chính xác cho phần này trong dữ liệu Co.opSmile. "
                "Anh/chị vui lòng kiểm tra trực tiếp trên website hoặc tại cửa hàng. "
                "Nếu cần, cho mình biết mặt hàng đang tìm để mình tra catalog ạ.")
    docs = "\n\n".join(f"[{h['title']}]\n{h['text']}" for h in hits)
    ctx = ""
    if category:
        ctx += f"BỐI CẢNH: khách đang được tư vấn nhóm sản phẩm '{category}' — trả lời cho đúng nhóm này.\n"
    recent = [m for m in (history or []) if m.get("content")][-6:]
    if recent:
        ctx += "Hội thoại gần nhất:\n" + "\n".join(
            f"{'Khách' if m.get('role') == 'user' else 'Trợ lý'}: {m['content'][:200]}" for m in recent) + "\n"
    if llm is not None:
        try:
            reply = (llm.complete_text(_system_prompt(addr, self_term),
                                       f"TÀI LIỆU:\n{docs}\n\n{ctx}Câu hỏi của khách: {query}") or "").strip()
            if reply and _numbers_grounded(reply, docs):
                log.info("policy: trả lời qua LLM grounded (chunks=%s)",
                         [h["title"] for h in hits])
                return reply
            log.warning("policy: LLM trả lời rỗng hoặc dính số lạ -> dùng nguyên văn tài liệu")
        except Exception as e:
            log.warning("policy: LLM lỗi (%s) -> dùng nguyên văn tài liệu", e)
    best = hits[0]
    return (f"Về {best['title'].lower()}, quy định hiện có như sau:\n\n{best['text']}\n\n"
            "Cần thêm thông tin nào khác không?")
