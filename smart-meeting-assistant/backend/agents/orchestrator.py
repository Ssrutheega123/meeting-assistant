import uuid

from agents.contradiction_agent import ContradictionAgent
from agents.risk_agent import RiskAgent
from agents.summary_agent import SummaryAgent
from agents.task_agent import TaskAgent
from models.meeting_models import MeetingProcessRequest, MeetingResult
from services.groq_service import GroqService
from services.mongodb_service import MongoDBService


class MeetingOrchestrator:
    def __init__(self, groq: GroqService, mongodb: MongoDBService) -> None:
        self.mongodb = mongodb
        self.summary_agent = SummaryAgent(groq)
        self.task_agent = TaskAgent(groq)
        self.risk_agent = RiskAgent(groq)
        self.contradiction_agent = ContradictionAgent(groq, mongodb)

    def process(self, request: MeetingProcessRequest) -> MeetingResult:
        meeting_id = request.meeting_id or str(uuid.uuid4())[:8]
        transcript = request.transcript.strip()

        summary = self.summary_agent.run(transcript)
        tasks = self.task_agent.run(transcript)
        risks = self.risk_agent.run(transcript)
        contradictions = self.contradiction_agent.run(meeting_id, summary)

        result = MeetingResult(
            meeting_id=meeting_id,
            title=request.title or "Untitled Meeting",
            transcript=transcript,
            summary=summary,
            tasks=tasks,
            risks=risks,
            contradictions=contradictions,
        )
        self.mongodb.save_meeting_result(result)
        return result
