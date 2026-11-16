from fastapi import FastAPI, Depends, HTTPException, status, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import jwt

from app.ingestor import start_f1_ingestion
from app.state_manager import state_manager
from app.ai_service import get_answer
from app.db import save_message, get_chat_history, create_user, get_user, clear_user_chats
from app.auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.football_ingestion import get_cached_league, get_match_context

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(start_f1_ingestion(session_id="f1_live"))]
    yield
    for task in tasks:
        task.cancel()

app = FastAPI(lifespan=lifespan)
def get_user_token(request: Request):
    return request.headers.get("Authorization", get_remote_address(request))
limiter = Limiter(key_func=get_user_token)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class AuthUser(BaseModel):
    username: str
    password: str

class UserQuery(BaseModel):
    question: str
    session_id: str = "f1_live"


@app.get("/")
async def serve_frontend():
    return FileResponse("app/static/index.html")

@app.post("/register")
async def register(user: AuthUser):
    hashed_pw = get_password_hash(user.password)
    success = create_user(user.username, hashed_pw)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "User created successfully"}

@app.post("/login")
async def login(user: AuthUser):
    print(f"\n--- LOGIN ATTEMPT: {user.username} ---")
    db_user = get_user(user.username)
    
    db_password = db_user.get('password') if db_user else None
    
    if not db_user or not db_password:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
        
    is_valid = verify_password(user.password, db_password)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    print("Clearing old chat history for fresh session...")
    clear_user_chats(user.username)
    
    access_token = create_access_token(data={"sub": user.username})
    print("Login Successful!\n")
    return {"access_token": access_token, "token_type": "bearer"}

# Protected Route: Requires Valid JWT
@app.get("/history/{session_id}")
async def fetch_history(session_id: str, current_user: str = Depends(get_current_user)):
    messages = get_chat_history(current_user, session_id)
    return {"messages": messages}

# Protected Route: Requires Valid JWT
@app.post("/ask")
@limiter.limit("5/minute")
async def ask_assistant(request: Request, query: UserQuery, current_user: str = Depends(get_current_user)):
    # Save user's question immediately
    save_message(current_user, query.session_id, query.question, True)

    if query.session_id.startswith("football_"):
        fixture_id = query.session_id.split("_")[-1]
        events_text = await get_match_context(fixture_id)
        state_snapshot = {"Match Timeline": events_text}
        answer = get_answer(query.question, state_snapshot, [])
        save_message(current_user, query.session_id, answer, False)
        return {"answer": answer, "state_snapshot": state_snapshot}
        
    else:
        context = state_manager.get_context(query.session_id)
        if not context["current_state"]:
            answer = f"No live data found for session: {query.session_id}"
            save_message(current_user, query.session_id, answer, False)
            return {"answer": answer}
        
        answer = get_answer(query.question, context["current_state"], context["recent_logs"])
        save_message(current_user, query.session_id, answer, False)
        
        return {"answer": answer, "state_snapshot": context["current_state"]}

@app.get("/state/{session_id}")
async def get_state(session_id: str):
    context = state_manager.get_context(session_id)
    return {"state": context.get("current_state", {})}

@app.get("/api/football/{league_key}")
async def api_get_football_league(league_key: str):
    """Fetches matches for a specific league on-demand."""
    matches = await get_cached_league(league_key)
    return {"matches": matches}