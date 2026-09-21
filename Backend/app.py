"""Minimal FastAPI smoke test."""

from fastapi import FastAPI

app = FastAPI(title="FedRetina Smoke Test")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "fedretina-backend"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "fedretina-backend", "docs": "/docs"}