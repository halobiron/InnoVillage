from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import sqlite3
from app.schemas import AdviceResult, FactCard
from app.agent_core.presenters import build_reco_card
from app.agent_core.retriever import get_catalog_metadata
from app.advice.provenance import facts_for_llm, format_vnd
from app.advice.verify import allowed_numbers, line_is_grounded, verify_advice, is_grounded

log = logging.getLogger("agent_core")


def _system_prompt(addr: str, self_term: str) -> str:
    del addr, self_term
    return (
        "Bạn là nhân viên tư vấn hàng tiêu dùng thiết yếu của Co.opSmile. NGUYÊN TẮC:\n"
        "1. CHỈ dùng đúng các con số xuất hiện trong FACTS (giá, thông số). TUYỆT ĐỐI không nêu bất kỳ "
        "con số nào KHÔNG có trong FACTS — không ước lượng tiền điện/tháng, không tự tính mức tiết kiệm, "
        "không đưa phần trăm/kWh/nghìn đồng suy diễn. Nếu muốn nói về lợi ích, hãy mô tả BẰNG LỜI, không kèm số.\n"
        "1b. Viết MỌI con số Y HỆT định dạng trong FACTS (ví dụ giá '10.010.000đ' phải giữ nguyên, "
        "KHÔNG đổi sang '10 triệu' hay '10,01 triệu'; thông số giữ nguyên đơn vị như FACTS).\n"
        "1c. KHÔNG cộng/gộp/tính tổng hay làm tròn các con số (ví dụ KHÔNG cộng dung tích ngăn đá + ngăn "
        "lạnh thành 'tổng ~330 lít'); chỉ nêu lại từng con số đúng như FACTS.\n"
        "2. Chọn USP có ích cho quyết định mua: nối tiêu chí khách nêu với khác biệt cụ thể trong FACTS "
        "(ví dụ vừa ngân sách, dung tích phù hợp, kích thước/khả năng lắp đặt, độ ồn, điện năng, bảo hành "
        "nếu có dữ liệu). Nói rõ lợi ích thực tế bằng lời khi suy luận đó hợp lý từ thông số; không biến tên "
        "công nghệ thành lợi ích nếu chưa giải thích được nó giúp gì cho nhu cầu này. Không tự đưa ra công dụng, "
        "hiệu quả sức khỏe, thành phần hay cam kết mà dữ liệu không nêu. Nếu không có khác biệt hữu ích được "
        "chứng minh, hãy nói trung tính thay vì bịa USP.\n"
        "3. Phân tích đánh đổi (trade-off) rõ giữa các lựa chọn để khách dễ quyết.\n"
        "4. Nếu trạng thái là price_spread: khách nhờ chọn giúp và chưa chốt ngân sách — giải thích rằng "
        "các lựa chọn đại diện cho 3 tầm giá (tiết kiệm / tầm trung / cao cấp), rồi giới thiệu từng mức.\n"
        "4b. Nếu trạng thái là custom_query: danh sách đã lọc đúng theo ràng buộc thông số khách nêu — "
        "nêu bật thông số đáp ứng ràng buộc đó (chỉ dùng số trong FACTS).\n"
        "4d. Nếu kết quả trả về KHÔNG KHỚP HOÀN TOÀN với yêu cầu của khách (ví dụ: vượt ngân sách, khác thương hiệu, thiếu tính năng), BẮT BUỘC phải nói rõ sự sai lệch này (VD: 'Mẫu này vượt ngân sách một chút', 'Mẫu này không hỗ trợ tính năng X'). TUYỆT ĐỐI không tự bịa tính năng để ép cho khớp.\n"
        "4e. ĐẶC BIỆT NHẤN MẠNH vào tiêu chí khách đã nêu (như loại sản phẩm, dung tích, mùi hương), "
        "chỉ kết luận khi FACTS có thông tin xác nhận.\n"
        "4f. Nếu không tìm thấy sản phẩm nào (FACTS trống rỗng), hãy lịch sự xin lỗi khách, giải thích lý do (dựa trên yêu cầu của khách không có trong dữ liệu) và đóng vai một người sale chuyên nghiệp để hỏi gợi mở sang một nhu cầu/tiêu chí khác. TUYỆT ĐỐI KHÔNG đề xuất máy móc khi FACTS trống.\n"
        "5. Giọng chuyên nghiệp, mạch lạc, súc tích, đúng ngữ pháp.\n"
        "5b. Chỉ dùng cách xưng hô khi khách đã thể hiện rõ trong hội thoại. Nếu không chắc, viết câu trung tính, "
        "không tự gán tuổi, giới tính hay vai vế.\n"
        "6. KHÔNG dùng định dạng Markdown (tuyệt đối không dùng dấu sao `*` hoặc `#` để in đậm/in nghiêng). Để tạo danh sách, hãy xuống dòng và dùng dấu `-` hoặc số `1.` bình thường."
    )


def build_cards(rows: List[Dict[str, Any]], priority_features: List[str],
                self_term: str = "em") -> List[FactCard]:
    return [build_reco_card(r, priority_features, self_term=self_term) for r in rows]


def deterministic_message(intent: Dict[str, Any], status: str, db_path: Optional[str] = None,
                          addr: str = "") -> Optional[str]:
    """Copy tất định cho các trạng thái không cần LLM; None nếu cần LLM."""
    if status == "meta_inquiry":
        meta = get_catalog_metadata(db_path)
        cats = ", ".join(f"**{c}**" for c in meta["categories"])
        return (f"Hiện có **{len(meta['categories'])} danh mục** chính:\n\n{cats}\n\n"
                "Cần tư vấn danh mục nào, với ngân sách và tính năng ra sao?")
    if status == "no_products_found":
        category = intent.get("category") or "nhóm sản phẩm này"
        budget = intent.get("budget_max")
        requested_type = intent.get("requested_product_type")
        if db_path and budget and requested_type:
            try:
                with sqlite3.connect(db_path) as conn:
                    row = conn.execute(
                        "SELECT MIN(price_clean) FROM all_products "
                        "WHERE category = ? AND LOWER(product_name) LIKE LOWER(?) "
                        "AND price_clean > 0 AND price_clean > ?",
                        (category, f"%{requested_type}%", budget),
                    ).fetchone()
                if row and row[0]:
                    closest = int(row[0])
                    increase = closest - int(budget)
                    return (f"Chưa có {requested_type} trong ngân sách tối đa {format_vnd(int(budget))}. "
                            f"Sản phẩm gần nhất là {format_vnd(closest)}, tức cần tăng thêm "
                            f"{format_vnd(increase)}. Bạn có muốn nâng ngân sách lên {format_vnd(closest)} không?")
            except (sqlite3.Error, TypeError, ValueError):
                pass
        if db_path and budget and not requested_type:
            try:
                with sqlite3.connect(db_path) as conn:
                    row = conn.execute(
                        "SELECT MIN(price_clean) FROM all_products WHERE category = ? "
                        "AND price_clean > 0 AND price_clean > ?", (category, budget)
                    ).fetchone()
                if row and row[0]:
                    return (f"Chưa có sản phẩm {category} nào trong dữ liệu ở mức tối đa "
                            f"{format_vnd(int(budget))}. Mức giá gần nhất phía trên là "
                            f"{format_vnd(int(row[0]))}. Có thể tăng ngân sách lên khoảng "
                            f"{format_vnd(int(row[0]))}, hoặc giữ mức {format_vnd(int(budget))} "
                            "và bỏ bớt yêu cầu về loại, mùi hương hay thương hiệu. Bạn muốn thử cách nào?")
            except (sqlite3.Error, TypeError, ValueError):
                pass
        if requested_type and budget:
            return (f"Chưa tìm thấy {requested_type} phù hợp trong catalog với ngân sách tối đa "
                    f"{format_vnd(int(budget))}. Bạn muốn tăng ngân sách hay đổi sang mặt hàng khác?")
        if requested_type:
            return f"Catalog hiện chưa có sản phẩm {requested_type} để gợi ý. Bạn muốn xem mặt hàng nào khác?"
        if budget:
            return (f"Chưa có sản phẩm {category} nào trong dữ liệu vừa đúng ngân sách tối đa "
                    f"{format_vnd(int(budget))} vừa khớp các tiêu chí đã nêu. Có thể giữ ngân sách "
                    "và bỏ yêu cầu về loại, mùi hương hoặc thương hiệu; hoặc tăng ngân sách. "
                    "Bạn muốn nới tiêu chí nào trước?")
        return (f"Chưa có sản phẩm phù hợp trong dữ liệu cho {category}. "
                "Có thể bỏ yêu cầu về loại, mùi hương hoặc thương hiệu để tìm thêm. "
                "Bạn muốn nới tiêu chí nào trước?")
    return None


def generate_value_comparison_sentence(rows: List[Dict[str, Any]], priority_features: List[str],
                                       addr: str = "") -> Tuple[str | None, float | None]:
    """
    Sinh câu so sánh giá trị:
    'Với thêm X đồng, {addr} được thêm [tính năng khách ưu tiên] ở mẫu Y'
    Trả về (câu_so_sánh, số_tiền_chênh_lệch_để_cho_phép).
    """
    from app.agent_core.presenters import load_specs, _price_value, product_display_name
    
    if not priority_features or len(rows) < 2:
        return None, None

    # Sắp xếp các sản phẩm theo giá tăng dần
    sorted_rows = []
    for r in rows:
        p = _price_value(r)
        if p > 0:
            sorted_rows.append((p, r))
    
    if len(sorted_rows) < 2:
        return None, None
        
    sorted_rows.sort(key=lambda x: x[0])
    
    # Lấy mẫu rẻ nhất p1
    p1_price, p1 = sorted_rows[0]
    p1_specs = load_specs(p1)
    best_p2 = None
    best_features: List[tuple[str, str]] = []
    
    for p2_price, p2 in sorted_rows[1:]:
        p2_specs = load_specs(p2)
        p1_specs_lower = {k.lower(): v.lower() for k, v in p1_specs.items()}
        p2_specs_lower = {k.lower(): v.lower() for k, v in p2_specs.items()}
        
        # Tìm khác biệt có dữ liệu ở tiêu chí ưu tiên, không coi tên field
        # giống nhau đồng nghĩa hai mẫu có cùng giá trị.
        matched = []
        for f in priority_features:
            f_low = f.lower()
            fields_in_p2 = [(k, p2_specs[k]) for k, v in p2_specs_lower.items()
                            if f_low in k or f_low in v]
            for field, value in fields_in_p2:
                p1_value = next((v for k, v in p1_specs.items() if k.lower() == field.lower()), None)
                if p1_value is None or p1_value.strip().lower() != value.strip().lower():
                    matched.append((field, value))
        
        if matched:
            best_p2 = (p2_price, p2)
            best_features = matched
            break
            
    if not best_p2:
        return None, None
            
    p2_price, p2 = best_p2
    price_diff = p2_price - p1_price
    if price_diff <= 0:
        return None, None
        
    diff_str = format_vnd(int(price_diff))
    features_str = "; ".join(f"{field}: {value}" for field, value in best_features)
    p2_name = product_display_name(p2)
    
    sentence = f"So với mẫu thấp giá nhất, thêm {diff_str} chọn mẫu {p2_name} với khác biệt {features_str}."
    return sentence, price_diff


def generate_advisor(query: str, intent: Dict[str, Any], rows: List[Dict[str, Any]],
                     status: str, llm, cards: List[FactCard],
                     on_delta: Optional[Callable[[str], None]] = None,
                     addr: str = "", self_term: str = "",
                     db_path: Optional[str] = None) -> Tuple[str, bool, List[str]]:
    """Sinh tư vấn top-3 + trade-off. Trả (message, streamed, warnings). Fail-closed nếu bịa số."""
    det = deterministic_message(intent, status, db_path, addr=addr)
    if det is not None:
        log.info("advisor: dùng văn mẫu tất định (status=%s), không gọi LLM", status)
        return det, False, []

    facts = facts_for_llm(cards)
    assump = [a for a in (intent.get("assumptions") or []) if a]
    assump_txt = ("Giả định đang dùng (phải nói rõ với khách rằng đây chỉ là giả định): "
                  f"{'; '.join(assump)}\n" if assump else "")
    transition = intent.get("transition_message")
    trans_txt = f"LỜI CHUYỂN TIẾP (BẮT BUỘC dùng câu này làm câu mở đầu để giải thích sự suy luận): {transition}\n" if transition else ""
    
    wants_comp = intent.get("wants_comparison", False)
    # Chỉ dùng lời mời xem tiếp ngắn khi đây là một đề xuất đơn, không phải bảng so sánh.
    is_single_recommend = not wants_comp and len(cards) > 0
    if is_single_recommend:
        # Lời mời xem tiếp do code chèn thêm sau (closing_hook), KHÔNG để LLM tự hỏi
        # lại kiểu "xem thêm lựa chọn khác" — tránh trùng lặp CTA.
        action = (
            "Hãy ĐỀ XUẤT NGẮN GỌN 1-2 sản phẩm phù hợp nhất. Với mỗi mẫu, chọn 2-3 USP có sức nặng "
            "đối với nhu cầu/đánh đổi của khách; ưu tiên lợi ích sử dụng hoặc giá trị so với giá, rồi mới "
            "đến công nghệ. Mỗi USP phải nối được dữ kiện FACTS với nhu cầu khách, không liệt kê spec rời rạc."
        )
    else:
        action = "Hãy tư vấn các sản phẩm kèm phân tích đánh đổi (trade-off) chi tiết giữa các lựa chọn."
        
    user = (f"Trạng thái tìm kiếm: {status}\nFACTS (chỉ dùng dữ kiện này):\n{facts}\n\n"
            f"Nhu cầu khách: {query}\n{assump_txt}{trans_txt}{action}")

    # Tính toán câu so sánh giá trị nếu khách hỏi theo ngân sách và có priority_features
    comp_sentence = None
    extra_allowed_nums = set()
    budget_max = intent.get("budget_max")
    priority_features = intent.get("priority_features", [])
    
    if budget_max is not None and priority_features and len(rows) >= 2:
        comp_sentence, price_diff = generate_value_comparison_sentence(rows, priority_features, addr=addr)
        if price_diff:
            from app.advice.verify import extract_numbers
            extra_allowed_nums.update(extract_numbers(format_vnd(int(price_diff))))

    # Đừng tự chèn phí giao/lắp và CTA đặt hàng vào lời đề xuất. Khách chưa chọn
    # máy và chưa hỏi chính sách; phần này chỉ được trả lời ở nhánh policy hoặc
    # sau khi khách xác nhận mua.
    closing_line = None

    # Streaming: phát từng dòng đã verify (line-level fail-closed).
    system = _system_prompt(addr, self_term)
    if on_delta is not None:
        allowed = allowed_numbers(cards)
        if extra_allowed_nums:
            allowed.update(extra_allowed_nums)
        parts: List[str] = []
        buf = ""

        def push(line: str) -> None:
            if line:
                on_delta(line)

        try:
            for token in llm.stream_text(system, user):
                parts.append(token)
                buf += token
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    push(line + "\n")
            if buf:
                push(buf)
                
            if comp_sentence:
                push("\n\n" + comp_sentence)
                parts.append("\n\n" + comp_sentence)
            if closing_line:
                push("\n\n" + closing_line)
                parts.append("\n\n" + closing_line)
        except Exception:
            return _blocking(llm, system, user, cards, self_term, comp_sentence, extra_allowed_nums, closing_line)

        result = verify_advice(
            AdviceResult(message="".join(parts), cards=cards, assumptions=[], warnings=[]),
            extra_allowed=extra_allowed_nums
        )
        if not is_grounded(result):
            log.warning("advisor(stream): LLM vi phạm lỗi số liệu, cảnh báo (warnings=%s)", list(result.warnings))
            return _safe_summary(cards, self_term), False, list(result.warnings)
        log.info("advisor(stream): câu trả lời LLM grounded, phát đủ")
        return result.message, True, []

    return _blocking(llm, system, user, cards, self_term, comp_sentence, extra_allowed_nums, closing_line)


def _blocking(llm, system: str, user: str, cards: List[FactCard], self_term: str = "",
              comp_sentence: Optional[str] = None,
              extra_allowed_nums: Optional[set[str]] = None, closing_line: Optional[str] = None) -> Tuple[str, bool, List[str]]:
    try:
        message = llm.complete_text(system, user)
    except Exception as e:
        log.warning("advisor: LLM lỗi (%s) -> safe summary", e)
        summary = _safe_summary(cards, self_term)
        if closing_line:
            summary = summary + "\n\n" + closing_line
        return summary, False, []

    if comp_sentence:
        message = message.strip() + "\n\n" + comp_sentence
    if closing_line:
        message = message.strip() + "\n\n" + closing_line

    result = verify_advice(
        AdviceResult(message=message, cards=cards, assumptions=[], warnings=[]),
        extra_allowed=extra_allowed_nums
    )
    if not is_grounded(result):
        log.warning("advisor: LLM vi phạm lỗi số liệu, cảnh báo (warnings=%s)", list(result.warnings))
        summary = _safe_summary(cards, self_term)
        if closing_line:
            summary = summary + "\n\n" + closing_line
        return summary, False, list(result.warnings)
    log.info("advisor: câu trả lời LLM grounded")
    return result.message, False, []


def _safe_summary(cards: List[FactCard], self_term: str = "") -> str:
    del self_term
    lines = ["Các máy dưới đây được gợi ý từ thông tin trực tiếp trong catalog:"]
    for i, c in enumerate(cards, 1):
        price = next((l.value for l in c.lines if l.label == "Giá"), "chưa có dữ liệu")
        # Tiêu đề card có dạng "Vì sao {self_term} đề xuất {name}?" — self_term đổi theo khách.
        title = c.title.split(" đề xuất ", 1)[-1].rstrip("?") if " đề xuất " in c.title else c.title.rstrip("?")
        url = next((l.value for l in c.lines if l.label == "Link sản phẩm"), "")
        url_text = f" - Xem chi tiết: {url}" if url else ""
        lines.append(f"{i}. {title} — giá {price}.{url_text}")
    return "\n".join(lines)
