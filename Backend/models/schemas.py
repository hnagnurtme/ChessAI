from pydantic import BaseModel, Field
from typing import Optional


class MoveRequest(BaseModel):
    """Body gửi lên để lấy nước đi tốt nhất."""

    fen: str = Field(
        ...,
        description="FEN string biểu diễn trạng thái bàn cờ hiện tại.",
        example="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    )
    engine: str = Field(
        default="vip",
        description='Engine sử dụng: "v1" (đơn giản), "v2" (trung bình), "vip" (mạnh nhất).',
    )
    depth: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Độ sâu tìm kiếm (1-10). Chỉ áp dụng cho v1 và v2.",
    )
    time_limit: float = Field(
        default=1.0,
        ge=0.1,
        le=30.0,
        description="Giới hạn thời gian suy nghĩ (giây). Chỉ áp dụng cho engine VIP.",
    )


class MoveResponse(BaseModel):
    """Kết quả trả về sau khi tính toán."""

    move: str = Field(..., description='Nước đi tốt nhất ở dạng UCI, ví dụ "e2e4".')
    engine_used: str = Field(..., description="Tên engine đã dùng.")
    nodes: Optional[int] = Field(None, description="Số node đã duyệt (nếu engine hỗ trợ).")
    elapsed_ms: Optional[float] = Field(None, description="Thời gian tính toán (ms).")


class EngineInfo(BaseModel):
    """Thông tin một engine."""

    name: str
    description: str
    supports_time_limit: bool


class EnginesResponse(BaseModel):
    engines: list[EngineInfo]
