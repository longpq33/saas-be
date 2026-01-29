import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router

app = FastAPI(title="DND SaaS Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _get_port() -> int:
    port_raw = os.getenv("PORT", "8000")
    try:
        return int(port_raw)
    except ValueError:
        return 8000


def _get_host() -> str:
    return os.getenv("HOST", "0.0.0.0")


if __name__ == "__main__":
    uvicorn.run("main:app", host=_get_host(), port=_get_port())
