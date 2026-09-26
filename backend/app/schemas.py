from __future__ import annotations
from pydantic import BaseModel, Field

class FactLine(BaseModel):
    label: str
    value: str
    source: str


class ReviewItem(BaseModel):
    author: str | None = None
    rating: float | None = None
    content: str


class FactCard(BaseModel):
    title: str
    lines: list[FactLine] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    productidweb: str | None = None
    image_url: str | None = None
    product_link: str | None = None
    stock_status: str | None = None      # Tình trạng tồn kho nếu nguồn catalog cung cấp
    rating: float | None = None          # điểm đánh giá trung bình
    review_count: int | None = None      # số lượt đánh giá
    installment: str | None = None       # thông tin trả góp
    reviews: list[ReviewItem] = Field(default_factory=list)


class ComparisonCell(BaseModel):
    value: str                      # "12.400.000đ", "300 kWh/năm", hoặc "chưa có dữ liệu"
    available: bool = True
    is_best: bool = False           # ứng viên tốt nhất theo tiêu chí của hàng này
    status: str | None = None       # "good" / "warn" / "bad" — đèn tín hiệu cho hàng theo nhu cầu
    verdict: str | None = None      # nhãn ngắn: "Dư sức mua", "Vượt trội", ... (rút ra từ số liệu thật)
    detail: str | None = None       # câu giải thích, luôn dựng từ giá trị thật trong DB, không suy diễn


class ComparisonRow(BaseModel):
    label: str                      # "Giá", "Điện năng tiêu thụ", "Thương hiệu"
    unit: str | None = None
    source: str                     # "catalog" / "thông số nhà sản xuất"
    cells: list[ComparisonCell] = Field(default_factory=list)   # 1 ô / sản phẩm, cùng thứ tự với products
    better: str | None = None       # gợi ý đọc: "giá thấp hơn tốt hơn", ...
    is_need_row: bool = False       # true nếu hàng gắn với ngân sách/nhu cầu khách nêu (render kiểu đèn tín hiệu)


class ComparisonTradeoffPoint(BaseModel):
    """Một tín hiệu đã có mặt trong bảng, giữ nguyên field và giá trị nguồn."""
    label: str
    value: str
    verdict: str | None = None


class ComparisonTradeoff(BaseModel):
    """Tóm tắt có cấu trúc cho một sản phẩm, không tự diễn dịch thành câu tư vấn."""
    strengths: list[ComparisonTradeoffPoint] = Field(default_factory=list)
    considerations: list[ComparisonTradeoffPoint] = Field(default_factory=list)


class ComparisonTable(BaseModel):
    products: list[str] = Field(default_factory=list)          # tên cột (display_name các ứng viên)
    rows: list[ComparisonRow] = Field(default_factory=list)
    tradeoffs: list[ComparisonTradeoff] | None = None  # cùng thứ tự với products


class AdviceResult(BaseModel):
    message: str
    cards: list[FactCard] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    comparison: ComparisonTable | None = None
