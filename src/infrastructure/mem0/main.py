import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI()
MEMORY_PATH = Path("/app/memory")
MEMORY_PATH.mkdir(parents=True, exist_ok=True)


@app.get(
    "/ping",
    response_model=dict[str, str],
)
async def ping() -> dict[str, str]:
    """Health check endpoint for the memory module."""
    return {"status": "mem0 alive"}


@app.get(
    "/memory/{memory_id}",
    response_model=dict[str, Any],
)
async def read_memory(memory_id: str) -> dict[str, Any]:
    """Retrieve stored memory by ID."""
    file_path = MEMORY_PATH / f"{memory_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Memory not found")
    try:
        data: dict[str, Any] = json.loads(file_path.read_text(encoding="utf-8"))
        return data
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to decode memory JSON",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read memory file") from e


@app.post(
    "/memory/{memory_id}",
    response_model=dict[str, Any],
)
async def write_memory(memory_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Store memory data by ID."""
    file_path = MEMORY_PATH / f"{memory_id}.json"
    try:
        file_path.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return {"status": "success", "id": memory_id}
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to write memory file",
        ) from e
