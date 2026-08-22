from dotenv import load_dotenv
import os

load_dotenv()  # must run before anything imports app.llm.llm_client, which reads
# LLM_BACKEND / GEMINI_API_KEY from the environment at import time

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.metrics import router as metrics_router  # noqa: E402
from app.routes.products import router as products_router  # noqa: E402
from app.store import init_db  # noqa: E402

app = FastAPI(title="UniHack Product Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        *([os.environ["FRONTEND_ORIGIN"]] if os.environ.get("FRONTEND_ORIGIN") else []),
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(metrics_router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
