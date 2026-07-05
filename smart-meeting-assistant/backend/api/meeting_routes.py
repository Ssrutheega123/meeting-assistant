from fastapi import APIRouter, HTTPException

from agents.orchestrator import MeetingOrchestrator
from models.meeting_models import MeetingProcessRequest
from services.groq_service import GroqService
from services.mongodb_service import MongoDBService


router = APIRouter(prefix="/api", tags=["meetings"])

mongodb = MongoDBService()
groq = GroqService()
orchestrator = MeetingOrchestrator(groq, mongodb)


@router.post("/process-meeting")
def process_meeting(request: MeetingProcessRequest):
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    try:
        result = orchestrator.process(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "meeting_id": result.meeting_id,
        "summary": result.summary.model_dump(),
        "tasks": [task.model_dump() for task in result.tasks],
        "risks": [risk.model_dump() for risk in result.risks],
        "contradictions": [item.model_dump() for item in result.contradictions],
    }


@router.get("/meetings")
def get_meetings():
    return mongodb.list_meetings()


@router.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: str):
    meeting = mongodb.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/tasks")
def get_tasks():
    return mongodb.list_tasks()


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, payload: dict):
    status = str(payload.get("status") or "pending")
    updated = mongodb.update_task_status(task_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "updated", "task_id": task_id}


@router.get("/stats")
def get_stats():
    return mongodb.stats()
