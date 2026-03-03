"""
FastAPI entry point — Chess Bot API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

app = FastAPI(
    title="Chess Bot API",
    description=(
        "API cho chess bot với 3 engine:\n"
        "- **v1**: Alpha-Beta đơn giản\n"
        "- **v2**: Iterative Deepening + TT + LMR\n"
        "- **vip**: Engine mạnh nhất (SEE, Aspiration Window, Pawn Hash)"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — cho phép frontend hoặc client khác gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(router, prefix="/api")


# ── Health check ─────────────────────────────────────────
@app.get("/health", tags=["System"], summary="Health check")
def health():
    return {"status": "ok"}
