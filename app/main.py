from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio

from app.ingestor import start_f1_ingestion # start_football_ingestion, start_cricket_ingestion
from app.state_manager import state_manager
from app.ai_service import get_answer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Spin up multiple distinct ingestors. 
    # assign custom session IDs that the frontend will request.
    tasks = [
        asyncio.create_task(start_f1_ingestion(session_id="f1_live")),
    ]
    yield
    for task in tasks:
        task.cancel()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class UserQuery(BaseModel):
    question: str
    session_id: str = "f1_live"  # Default to F1, frontend can override this later

@app.get("/")
async def serve_frontend():
    return FileResponse("app/static/index.html")

@app.post("/ask")
async def ask_assistant(query: UserQuery):
    # Fetch context specific to the requested sport/game
    context = state_manager.get_context(query.session_id)
    
    if not context["current_state"]:
        return {"answer": f"No live data found for session: {query.session_id}"}
        
    answer = get_answer(
        user_query=query.question, 
        current_state=context["current_state"], 
        recent_logs=context["recent_logs"]
    )
    return {"answer": answer, "state_snapshot": context["current_state"]}

@app.get("/state/{session_id}")
async def get_state(session_id: str):
    # This allows the frontend to poll the live scoreboard silently
    context = state_manager.get_context(session_id)
    return {"state": context.get("current_state", {})}