# MeetMind — AI Meeting Assistant

A multi-agent AI system that processes meeting transcripts using 3 parallel sub-agents.

## Architecture

```
User Input (Transcript)
        │
        ▼
  Orchestrator Agent
   /      |      \
  ▼       ▼       ▼
Task    Calendar  Notes
Agent    Agent    Agent
  \       |      /
   ▼      ▼     ▼
      SQLite DB
        │
        ▼
    FastAPI REST
        │
        ▼
  Dark UI Dashboard
```

## Quick Start

### Prerequisites
- Python 3.9+
- Groq API key (get one at https://console.groq.com)

### Run (Mac/Linux)
```bash
chmod +x start.sh
./start.sh
```

### Run (Windows)
Double-click `start.bat`

### Manual run
```bash
cd backend
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here   # Mac/Linux
set GROQ_API_KEY=your_key_here      # Windows
export GROQ_MODEL=llama-3.3-70b-versatile
python main.py
```

Then open http://localhost:8000 in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/process-meeting | Process transcript (main endpoint) |
| GET | /api/tasks | Get all extracted tasks |
| PATCH | /api/tasks/:id | Update task status |
| GET | /api/calendar | Get all scheduled events |
| GET | /api/meetings | Meeting history |
| GET | /api/stats | Dashboard statistics |

## Agent Roles

| Agent | Role |
|-------|------|
| **Orchestrator** | Coordinates all sub-agents, manages meeting lifecycle |
| **Task Extractor** | Identifies action items, assignees, deadlines, priorities |
| **Calendar Agent** | Extracts meetings, events, scheduled follow-ups |
| **Notes Agent** | Writes summary, key decisions, follow-up email |

## Tech Stack
- **Backend**: Python, FastAPI, SQLite, Groq API (llama-3.3-70b-versatile model)
- **Frontend**: Vanilla HTML/CSS/JS (zero dependencies)
- **AI**: Groq's llama-3.3-70b-versatile model (3 parallel agent calls)
