from models.meeting_models import RiskItem, ensure_list
from services.groq_service import GroqService


class RiskAgent:
    def __init__(self, groq: GroqService) -> None:
        self.groq = groq

    def run(self, transcript: str) -> list[RiskItem]:
        response = self.groq.call_json(
            "You are the Risk Agent for MeetMind. Return only valid JSON.",
            f"""Detect simple project risks in this meeting transcript.

Look for:
- Deadline conflicts
- Missing task owners
- Missing deadlines
- Dependency issues
- Resource overload

Return exactly this JSON shape:
{{
  "risks": [
    {{
      "risk_type": "deadline_conflict | missing_owner | missing_deadline | dependency_issue | resource_overload | other",
      "severity": "low | medium | high",
      "description": "clear risk explanation",
      "recommendation": "practical next step"
    }}
  ]
}}

If no risks exist, return {{"risks": []}}.

Transcript:
{transcript}""",
            fallback={"risks": []},
        )
        risks: list[RiskItem] = []
        for item in ensure_list(response.get("risks")):
            if not isinstance(item, dict):
                continue
            description = str(item.get("description", "")).strip()
            if not description:
                continue
            risks.append(
                RiskItem(
                    risk_type=str(item.get("risk_type") or "other"),
                    severity=str(item.get("severity") or "medium").lower(),
                    description=description,
                    recommendation=str(item.get("recommendation") or ""),
                )
            )
        return risks
