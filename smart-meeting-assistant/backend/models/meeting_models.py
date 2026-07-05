from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MeetingProcessRequest(BaseModel):
    meeting_id: str | None = None
    title: str | None = "Untitled Meeting"
    transcript: str = Field(..., min_length=1)


class SummaryResult(BaseModel):
    objective: str = ""
    discussion_points: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)


class TaskItem(BaseModel):
    id: str | None = None
    person: str = ""
    task: str = ""
    deadline: str = ""
    status: str = "pending"


class RiskItem(BaseModel):
    risk_type: str = ""
    severity: str = "medium"
    description: str = ""
    recommendation: str = ""


class ContradictionResult(BaseModel):
    contradiction: bool = False
    previous_decision: str = ""
    current_decision: str = ""
    recommendation: str = ""


class MeetingResult(BaseModel):
    meeting_id: str
    title: str = "Untitled Meeting"
    transcript: str
    summary: SummaryResult
    tasks: list[TaskItem] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    contradictions: list[ContradictionResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StatsResult(BaseModel):
    total_meetings: int = 0
    total_tasks: int = 0
    pending_tasks: int = 0
    total_risks: int = 0
    contradictions: int = 0


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]
