import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

load_dotenv(project_root / ".env", override=True)

try:
    from api.meeting_routes import router as meeting_router
except ModuleNotFoundError:  # pragma: no cover - fallback for alternate execution contexts
    from backend.api.meeting_routes import router as meeting_router

app = FastAPI(title="MeetMind - Multi-Agent AI Meeting Intelligence System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meeting_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "MeetMind"}


frontend_path = (backend_dir.parent / "frontend").resolve()
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
