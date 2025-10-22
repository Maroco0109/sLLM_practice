"""Minimal FastAPI app placeholder for local development."""

from fastapi import FastAPI

app = FastAPI(title="sLLM-KR Backend")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple health payload."""
    return {"status": "ok"}
