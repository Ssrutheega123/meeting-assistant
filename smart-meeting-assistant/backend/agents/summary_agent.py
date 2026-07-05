from models.meeting_models import SummaryResult, ensure_list
from services.groq_service import GroqService


class SummaryAgent:
    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    def run(self, transcript: str) -> SummaryResult:
        response = self.groq.call_json(
            "You are the Summary Agent for MeetMind. Return only valid JSON.",
            f"""Analyze this meeting transcript.

Return exactly this JSON shape:
{{
  "objective": "main meeting objective",
  "discussion_points": ["point 1", "point 2"],
  "decisions": ["decision 1", "decision 2"]
}}

Transcript:
{transcript}""",
            fallback={"objective": "", "discussion_points": [], "decisions": []},
        )
        return SummaryResult(
            objective=str(response.get("objective", "")),
            discussion_points=[str(item) for item in ensure_list(response.get("discussion_points"))],
            decisions=[str(item) for item in ensure_list(response.get("decisions"))],
        )
