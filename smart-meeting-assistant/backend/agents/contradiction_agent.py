from models.meeting_models import ContradictionResult, SummaryResult, ensure_list
from services.groq_service import GroqService
from services.mongodb_service import MongoDBService


class ContradictionAgent:
    def __init__(self, groq: GroqService, mongodb: MongoDBService) -> None:
        self.groq = groq
        self.mongodb = mongodb

    def run(self, meeting_id: str, summary: SummaryResult) -> list[ContradictionResult]:
        previous_decisions = self.mongodb.get_previous_decisions(meeting_id)
        current_decisions = summary.decisions
        if not previous_decisions or not current_decisions:
            return []

        response = self.groq.call_json(
            "You are the Contradiction Detection Agent for MeetMind. Return only valid JSON.",
            f"""Compare current meeting decisions with previous meeting decisions.

Previous decisions:
{previous_decisions}

Current decisions:
{current_decisions}

Detect true contradictions only. Example: "Deploy on AWS" versus "Deploy on Azure".

Return exactly this JSON shape:
{{
  "contradictions": [
    {{
      "contradiction": true,
      "previous_decision": "conflicting previous decision",
      "current_decision": "conflicting current decision",
      "recommendation": "how the team should resolve it"
    }}
  ]
}}

If there are no contradictions, return {{"contradictions": []}}.""",
            fallback={"contradictions": []},
        )
        contradictions: list[ContradictionResult] = []
        for item in ensure_list(response.get("contradictions")):
            if not isinstance(item, dict):
                continue
            contradictions.append(
                ContradictionResult(
                    contradiction=bool(item.get("contradiction", False)),
                    previous_decision=str(item.get("previous_decision") or ""),
                    current_decision=str(item.get("current_decision") or ""),
                    recommendation=str(item.get("recommendation") or ""),
                )
            )
        return [item for item in contradictions if item.contradiction]
