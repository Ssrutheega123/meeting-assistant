import os
from datetime import datetime
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from models.meeting_models import MeetingResult


class MongoDBService:
    def __init__(self) -> None:
        uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.environ.get("MONGODB_DB_NAME", "meetmind")
        self.client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[db_name]
        self.meetings: Collection = self.db["meetings"]
        self.meetings.create_index("meeting_id", unique=True)
        self.meetings.create_index("created_at")

    def save_meeting_result(self, result: MeetingResult) -> dict[str, Any]:
        document = result.model_dump(mode="json")
        self.meetings.update_one(
            {"meeting_id": result.meeting_id},
            {"$set": document},
            upsert=True,
        )
        return document

    def get_previous_decisions(self, current_meeting_id: str | None = None, limit: int = 20) -> list[str]:
        query: dict[str, Any] = {}
        if current_meeting_id:
            query["meeting_id"] = {"$ne": current_meeting_id}

        decisions: list[str] = []
        cursor = self.meetings.find(query, {"summary.decisions": 1}).sort("created_at", -1).limit(limit)
        for meeting in cursor:
            decisions.extend(meeting.get("summary", {}).get("decisions", []) or [])
        return [str(decision) for decision in decisions if str(decision).strip()]

    def get_meeting(self, meeting_id: str) -> dict[str, Any] | None:
        meeting = self.meetings.find_one({"meeting_id": meeting_id})
        return self._serialize(meeting) if meeting else None

    def list_meetings(self, limit: int = 25) -> list[dict[str, Any]]:
        cursor = self.meetings.find().sort("created_at", -1).limit(limit)
        return [self._serialize(meeting) for meeting in cursor]

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for meeting in self.meetings.find({}, {"meeting_id": 1, "title": 1, "tasks": 1}).sort("created_at", -1):
            for task in meeting.get("tasks", []) or []:
                task_copy = dict(task)
                task_copy["meeting_id"] = meeting.get("meeting_id")
                task_copy["meeting_title"] = meeting.get("title", "")
                tasks.append(task_copy)
        return tasks

    def update_task_status(self, task_id: str, status: str) -> bool:
        result = self.meetings.update_one(
            {"tasks.id": task_id},
            {"$set": {"tasks.$.status": status}},
        )
        return result.modified_count > 0

    def stats(self) -> dict[str, int]:
        meetings = list(self.meetings.find({}, {"tasks": 1, "risks": 1, "contradictions": 1}))
        tasks = [task for meeting in meetings for task in meeting.get("tasks", []) or []]
        risks = [risk for meeting in meetings for risk in meeting.get("risks", []) or []]
        contradictions = [
            item
            for meeting in meetings
            for item in meeting.get("contradictions", []) or []
            if item.get("contradiction")
        ]
        return {
            "total_meetings": len(meetings),
            "total_tasks": len(tasks),
            "pending_tasks": len([task for task in tasks if task.get("status") != "done"]),
            "total_risks": len(risks),
            "contradictions": len(contradictions),
        }

    @staticmethod
    def _serialize(document: dict[str, Any]) -> dict[str, Any]:
        document = dict(document)
        document.pop("_id", None)
        created_at = document.get("created_at")
        if isinstance(created_at, datetime):
            document["created_at"] = created_at.isoformat()
        return document
