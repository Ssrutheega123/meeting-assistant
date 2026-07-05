import uuid

from models.meeting_models import TaskItem, ensure_list
from services.groq_service import GroqService


class TaskAgent:
    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    def run(self, transcript: str) -> list[TaskItem]:
        response = self.groq.call_json(
            "You are the Task Agent for MeetMind. Return only valid JSON.",
            f"""Extract action items from this meeting transcript.

Return exactly this JSON shape:
{{
  "tasks": [
    {{
      "person": "assigned person or Unassigned",
      "task": "specific action item",
      "deadline": "deadline or empty string"
    }}
  ]
}}

If no tasks exist, return {{"tasks": []}}.

Transcript:
{transcript}""",
            fallback={"tasks": []},
        )
        tasks: list[TaskItem] = []
        for item in ensure_list(response.get("tasks")):
            if not isinstance(item, dict):
                continue
            task_text = str(item.get("task", "")).strip()
            if not task_text:
                continue
            tasks.append(
                TaskItem(
                    id=str(uuid.uuid4())[:8],
                    person=str(item.get("person") or "Unassigned"),
                    task=task_text,
                    deadline=str(item.get("deadline") or ""),
                )
            )
        return tasks
