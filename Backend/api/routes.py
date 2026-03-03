"""
API Routes — Tất cả các endpoint của Chess Bot API.
"""

import time
import chess
from fastapi import APIRouter, HTTPException

from models.schemas import (
    MoveRequest,
    MoveResponse,
    EngineInfo,
    EnginesResponse,
)
from engines.bot_v1 import BotV1
from engines.bot_v2 import BotV2
from engines.bot_vip import BotVIP

router = APIRouter()

# ─────────────────────────────────────────────────────────
# Engine registry — thêm engine mới ở đây
# ─────────────────────────────────────────────────────────
_ENGINE_META = {
    "v1": EngineInfo(
        name="v1",
        description="Alpha-Beta đơn giản + Quiescence. Nhanh, nhẹ.",
        supports_time_limit=False,
    ),
    "v2": EngineInfo(
        name="v2",
        description="Iterative Deepening + TT + Null-move + LMR. Mạnh hơn V1.",
        supports_time_limit=False,
    ),
    "vip": EngineInfo(
        name="vip",
        description="Engine đầy đủ nhất: SEE, Aspiration Window, Pawn Hash, History. Mạnh nhất.",
        supports_time_limit=True,
    ),
}


def _make_engine(name: str):
    """Tạo engine instance theo tên. Mỗi request dùng instance riêng."""
    if name == "v1":
        return BotV1()
    if name == "v2":
        return BotV2()
    if name == "vip":
        return BotVIP()
    raise HTTPException(status_code=400, detail=f'Engine "{name}" không tồn tại. Chọn: v1, v2, vip.')


# ─────────────────────────────────────────────────────────
# GET /engines
# ─────────────────────────────────────────────────────────
@router.get(
    "/engines",
    response_model=EnginesResponse,
    summary="Liệt kê các engine",
    tags=["Engine"],
)
def list_engines() -> EnginesResponse:
    """Trả về danh sách engine và mô tả ngắn."""
    return EnginesResponse(engines=list(_ENGINE_META.values()))


# ─────────────────────────────────────────────────────────
# POST /move
# ─────────────────────────────────────────────────────────
@router.post(
    "/move",
    response_model=MoveResponse,
    summary="Lấy nước đi tốt nhất",
    tags=["Chess"],
)
def get_move(req: MoveRequest) -> MoveResponse:
    """
    Nhận FEN và tên engine → trả về nước đi tốt nhất (UCI format).

    - **fen**: Trạng thái bàn cờ (FEN string)
    - **engine**: `v1` | `v2` | `vip`
    - **depth**: Độ sâu (v1, v2)
    - **time_limit**: Giới hạn thời gian tính toán (chỉ VIP)
    """
    # Validate FEN
    try:
        board = chess.Board(req.fen)
    except ValueError:
        raise HTTPException(status_code=422, detail="FEN không hợp lệ.")

    if board.is_game_over():
        raise HTTPException(status_code=400, detail="Ván cờ đã kết thúc.")

    engine = _make_engine(req.engine)
    t0 = time.perf_counter()

    # Gọi engine
    if req.engine == "vip":
        move = engine.get_best_move(
            board,
            depth=req.depth,
            max_depth=req.depth,
            time_limit=req.time_limit,
        )
    else:
        move = engine.get_best_move(board, depth=req.depth)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    if move is None:
        raise HTTPException(status_code=500, detail="Engine không tìm được nước đi.")

    return MoveResponse(
        move=move.uci(),
        engine_used=req.engine,
        nodes=getattr(engine, "nodes", None),
        elapsed_ms=elapsed_ms,
    )
