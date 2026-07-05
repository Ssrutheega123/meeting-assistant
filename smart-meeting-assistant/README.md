# MeetMind

MeetMind is a simple Multi-Agent AI Meeting Intelligence System that turns meeting transcripts into structured meeting intelligence.

It uses FastAPI, MongoDB, and Groq's Llama model to generate summaries, action items, risk analysis, and contradiction checks against previous meeting history.

## Features

- Meeting summary generation
- Action item extraction with owner and deadline
- Project risk detection
- Contradiction detection using previous MongoDB meeting records
- FastAPI backend
- Simple frontend dashboard
- MongoDB storage
- Groq API integration


## Agent Architecture

```
Meeting Transcript
        |
        v
Orchestrator AI
   |        |        |          |
   v        v        v          v
Summary   Task     Risk   Contradiction
Agent     Agent    Agent      Agent
                              |
                              v
                    Previous Meeting Data
                           MongoDB
                              |
                              v
                       Final Result
                              |
                              v
                           MongoDB

```
## Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- Groq API
- PyMongo

### Database

- MongoDB

### Frontend

- HTML
- CSS
- JavaScript

## Project Structure

```text
smart-meeting-assistant/
|
├── backend/
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── summary_agent.py
│   │   ├── task_agent.py
│   │   ├── risk_agent.py
│   │   └── contradiction_agent.py
│   |
│   ├── api/
│   │   └── meeting_routes.py
│   |
│   ├── models/
│   │   └── meeting_models.py
│   |
│   ├── services/
│   │   ├── groq_service.py
│   │   └── mongodb_service.py
│   |
│   └── main.py
|
├── frontend/
│   └── index.html
|
├── requirements.txt
├── README.md
└── .env
```

## How It Works

1. The user submits a meeting transcript.
2. The orchestrator sends the transcript to four agents.
3. The Summary Agent extracts the objective, discussion points, and decisions.
4. The Task Agent extracts action items, owners, and deadlines.
5. The Risk Agent identifies project risks.
6. The Contradiction Agent compares current decisions with previous meeting decisions stored in MongoDB.
7. The final result is stored in MongoDB and returned to the frontend dashboard.

