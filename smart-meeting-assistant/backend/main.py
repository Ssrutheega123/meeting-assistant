import json
import os
import re
import sqlite3
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Smart Meeting Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/meetings.db")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# llama-3.3-70b-versatile: supports json_object, 12K TPM, works on free plan
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── Database Setup ───────────────────────────────────────────────────────────


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, assignee TEXT,
        due_date TEXT, priority TEXT, status TEXT DEFAULT 'pending',
        meeting_id TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS calendar_events (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, date TEXT, time TEXT,
        duration_minutes INTEGER, attendees TEXT, meeting_id TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS meeting_notes (
        id TEXT PRIMARY KEY, meeting_id TEXT, summary TEXT,
        key_decisions TEXT, follow_up_email TEXT, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS meetings (
        id TEXT PRIMARY KEY, title TEXT, status TEXT DEFAULT 'processing', created_at TEXT)""")
    conn.commit()
    conn.close()


init_db()

# ─── Groq API Call ────────────────────────────────────────────────────────────


def call_groq(system_msg: str, user_msg: str) -> dict:
    """Call Groq API with json_object mode — guaranteed to return valid JSON."""
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY environment variable not set")

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},  # llama-3.3-70b supports this
    }

    with httpx.Client(timeout=120) as http:
        resp = http.post(GROQ_URL, headers=headers, json=body)
        if resp.status_code == 429:
            raise Exception("Groq rate limit hit. Wait 60 seconds and try again.")
        if not resp.is_success:
            raise Exception(f"Groq API error {resp.status_code}: {resp.text}")
        content = resp.json()["choices"][0]["message"]["content"].strip()
        print(f"[GROQ {GROQ_MODEL}] response: {content[:300]}")
        return json.loads(content)


# ─── DB Save Helpers ──────────────────────────────────────────────────────────


def save_task(args: dict, meeting_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    tid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO tasks(id,title,assignee,due_date,priority,status,meeting_id,created_at) VALUES(?,?,?,?,?,'pending',?,?)",
        (
            tid,
            args.get("title", "Unnamed Task"),
            args.get("assignee", "Unassigned"),
            args.get("due_date", ""),
            args.get("priority", "medium"),
            meeting_id,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "created", "task_id": tid, "title": args.get("title")}


def save_event(args: dict, meeting_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    eid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO calendar_events(id,title,date,time,duration_minutes,attendees,meeting_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (
            eid,
            args.get("title", "Unnamed Event"),
            args.get("date", ""),
            args.get("time", "09:00"),
            args.get("duration_minutes", 60),
            json.dumps(args.get("attendees", [])),
            meeting_id,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "created", "event_id": eid, "title": args.get("title")}


def save_note(args: dict, meeting_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    nid = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO meeting_notes(id,meeting_id,summary,key_decisions,follow_up_email,created_at) VALUES(?,?,?,?,?,?)",
        (
            nid,
            meeting_id,
            args.get("summary", ""),
            json.dumps(args.get("key_decisions", [])),
            args.get("follow_up_email", ""),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "created", "note_id": nid}


# ─── Sub-Agent 1: Notes ───────────────────────────────────────────────────────


def notes_agent(transcript: str, meeting_id: str, today: str) -> dict:
    system = (
        "You are a meeting notes AI. You MUST respond with valid JSON only. "
        "No explanation, no markdown. Just a JSON object."
    )
    user = f"""Analyze this meeting transcript. Today is {today}.

Return this exact JSON:
{{
  "summary": "2-3 sentence summary of the meeting",
  "key_decisions": ["decision 1", "decision 2", "decision 3"],
  "follow_up_email": "Subject: Meeting Follow-up\\n\\nHi team,\\n\\n[full email body here]\\n\\nBest regards"
}}

TRANSCRIPT:
{transcript}"""

    parsed = call_groq(system, user)
    return save_note(
        {
            "summary": parsed.get("summary", ""),
            "key_decisions": parsed.get("key_decisions", []),
            "follow_up_email": parsed.get("follow_up_email", ""),
        },
        meeting_id,
    )


# ─── Sub-Agent 2: Tasks ───────────────────────────────────────────────────────


def tasks_agent(transcript: str, meeting_id: str, today: str) -> list:
    system = (
        "You are a task extraction AI. You MUST respond with valid JSON only. "
        "No explanation, no markdown. Just a JSON object."
    )
    user = f"""Extract all action items and tasks from this meeting transcript. Today is {today}.
For due dates: calculate real YYYY-MM-DD dates. "next Friday" = next Friday from {today}, "end of week" = this Friday, "next week" = +7 days from {today}.

Return this exact JSON:
{{
  "tasks": [
    {{
      "title": "what needs to be done",
      "assignee": "person's name or Unassigned",
      "due_date": "YYYY-MM-DD or empty string",
      "priority": "high or medium or low"
    }}
  ]
}}

If no tasks found return: {{"tasks": []}}

TRANSCRIPT:
{transcript}"""

    parsed = call_groq(system, user)
    results = []
    for task in parsed.get("tasks", []):
        if str(task.get("title", "")).strip():
            results.append(save_task(task, meeting_id))
    return results


# ─── Sub-Agent 3: Calendar ────────────────────────────────────────────────────


def calendar_agent(transcript: str, meeting_id: str, today: str) -> list:
    system = (
        "You are a calendar scheduling AI. You MUST respond with valid JSON only. "
        "No explanation, no markdown. Just a JSON object."
    )
    user = f"""Extract all meetings, events, and deadlines from this transcript. Today is {today}.
Calculate real YYYY-MM-DD dates from context clues.

Return this exact JSON:
{{
  "events": [
    {{
      "title": "event or meeting name",
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "duration_minutes": 60,
      "attendees": ["name1", "name2"]
    }}
  ]
}}

If no events found return: {{"events": []}}

TRANSCRIPT:
{transcript}"""

    parsed = call_groq(system, user)
    results = []
    for event in parsed.get("events", []):
        if str(event.get("title", "")).strip() and str(event.get("date", "")).strip():
            results.append(save_event(event, meeting_id))
    return results


# ─── Orchestrator ─────────────────────────────────────────────────────────────


def orchestrate(transcript: str, meeting_id: str) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    agent_log = []

    # Agent 1: Notes
    try:
        r = notes_agent(transcript, meeting_id, today)
        agent_log.append({"agent": "Notes Agent", "action": "create_meeting_note", "result": r})
    except Exception as e:
        print(f"[ERROR] Notes Agent: {e}")
        agent_log.append(
            {"agent": "Notes Agent", "action": "create_meeting_note", "result": {"error": str(e)}}
        )

    # Agent 2: Tasks
    try:
        results = tasks_agent(transcript, meeting_id, today)
        for r in results:
            agent_log.append({"agent": "Task Agent", "action": "create_task", "result": r})
        if not results:
            agent_log.append(
                {
                    "agent": "Task Agent",
                    "action": "create_task",
                    "result": {"status": "no tasks found"},
                }
            )
    except Exception as e:
        print(f"[ERROR] Task Agent: {e}")
        agent_log.append(
            {"agent": "Task Agent", "action": "create_task", "result": {"error": str(e)}}
        )

    # Agent 3: Calendar
    try:
        results = calendar_agent(transcript, meeting_id, today)
        for r in results:
            agent_log.append(
                {"agent": "Calendar Agent", "action": "create_calendar_event", "result": r}
            )
        if not results:
            agent_log.append(
                {
                    "agent": "Calendar Agent",
                    "action": "create_calendar_event",
                    "result": {"status": "no events found"},
                }
            )
    except Exception as e:
        print(f"[ERROR] Calendar Agent: {e}")
        agent_log.append(
            {
                "agent": "Calendar Agent",
                "action": "create_calendar_event",
                "result": {"error": str(e)},
            }
        )

    return {"agent_log": agent_log}


# ─── DB Fetch ─────────────────────────────────────────────────────────────────


def fetch_meeting_data(meeting_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    tasks = c.execute("SELECT * FROM tasks WHERE meeting_id=?", (meeting_id,)).fetchall()
    events = c.execute("SELECT * FROM calendar_events WHERE meeting_id=?", (meeting_id,)).fetchall()
    notes = c.execute("SELECT * FROM meeting_notes WHERE meeting_id=?", (meeting_id,)).fetchone()
    conn.close()
    return {
        "tasks": [dict(t) for t in tasks],
        "events": [{**dict(e), "attendees": json.loads(e["attendees"] or "[]")} for e in events],
        "notes": {**dict(notes), "key_decisions": json.loads(notes["key_decisions"] or "[]")}
        if notes
        else None,
    }


# ─── API Routes ───────────────────────────────────────────────────────────────


@app.post("/api/process")
@app.post("/api/process-meeting")
async def process_meeting(request: Request):
    raw = await request.body()
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw.decode("utf-8", errors="replace"))
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON body: {e}")

    transcript = payload.get("transcript", "").strip()
    title = payload.get("title", "Meeting") or "Meeting"

    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    meeting_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO meetings(id,title,status,created_at) VALUES(?,?,'processing',?)",
        (meeting_id, title, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    try:
        result = orchestrate(transcript, meeting_id)
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE meetings SET status='done' WHERE id=?", (meeting_id,))
        conn.commit()
        conn.close()
        return {
            "meeting_id": meeting_id,
            "status": "done",
            "agent_log": result["agent_log"],
            "data": fetch_meeting_data(meeting_id),
        }
    except Exception as e:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE meetings SET status='error' WHERE id=?", (meeting_id,))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    return fetch_meeting_data(meeting_id)


@app.get("/api/dashboard")
async def dashboard():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    meetings = c.execute("SELECT * FROM meetings ORDER BY created_at DESC LIMIT 20").fetchall()
    total_tasks = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    total_events = c.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    total_meetings = c.execute("SELECT COUNT(*) FROM meetings WHERE status='done'").fetchone()[0]
    conn.close()
    return {
        "meetings": [dict(m) for m in meetings],
        "stats": {"tasks": total_tasks, "events": total_events, "meetings": total_meetings},
    }


@app.get("/api/stats")
async def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    total_meetings = c.execute("SELECT COUNT(*) FROM meetings WHERE status='done'").fetchone()[0]
    total_tasks = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    pending_tasks = c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0]
    total_events = c.execute("SELECT COUNT(*) FROM calendar_events").fetchone()[0]
    conn.close()
    return {
        "total_meetings": total_meetings,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "total_events": total_events,
    }


@app.get("/api/tasks")
async def get_all_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    tasks = c.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(t) for t in tasks]


@app.get("/api/calendar")
async def get_all_events():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    events = c.execute("SELECT * FROM calendar_events ORDER BY date ASC").fetchall()
    conn.close()
    return [{**dict(e), "attendees": json.loads(e["attendees"] or "[]")} for e in events]


@app.get("/api/meetings")
async def get_all_meetings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    meetings = c.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(m) for m in meetings]


@app.delete("/api/tasks/{task_id}")
async def complete_task(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tasks SET status='completed' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"status": "updated"}


# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
