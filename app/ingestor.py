import asyncio
import httpx
from app.state_manager import state_manager

F1_BASE_URL = "https://api.openf1.org/v1"

async def fetch_latest_f1_session_key(client: httpx.AsyncClient) -> str:
    try:
        response = await client.get(f"{F1_BASE_URL}/sessions?session_key=latest")
        if response.status_code == 200 and response.json():
            return str(response.json()[0].get('session_key', 'latest'))
    except Exception as e:
        print(f"Error fetching F1 session: {e}")
    return "latest"

async def start_f1_ingestion(session_id: str):
    last_rc_date = None
    sport = "Formula 1"
    
    async with httpx.AsyncClient() as client:
        f1_session_key = await fetch_latest_f1_session_key(client)
        state_manager.update_state(session_id, sport, "session_key", f1_session_key)
        state_manager.add_log(session_id, sport, f"Connected to OpenF1 Live API. Key: {f1_session_key}")

        while True:
            try:
                # 1. Race Control Logic
                rc_resp = await client.get(f"{F1_BASE_URL}/race_control?session_key={f1_session_key}")
                if rc_resp.status_code == 200:
                    messages = sorted(rc_resp.json(), key=lambda x: x.get('date', ''))
                    for msg in messages:
                        msg_date = msg.get('date')
                        if not last_rc_date or msg_date > last_rc_date:
                            flag = msg.get('flag', '')
                            log_str = f"[RACE CONTROL] {flag} - {msg.get('message', '')}".strip(" -")
                            
                            state_manager.add_log(session_id, sport, log_str)
                            if flag:
                                state_manager.update_state(session_id, sport, "flags", flag)
                            last_rc_date = msg_date

                # 2. Leader Tracking Logic
                pos_resp = await client.get(f"{F1_BASE_URL}/positions?session_key={f1_session_key}")
                if pos_resp.status_code == 200 and pos_resp.json():
                    leaders = [p for p in pos_resp.json() if p.get('position') == 1]
                    if leaders:
                        latest_leader = max(leaders, key=lambda x: x.get('date', ''))
                        state_manager.update_state(session_id, sport, "leader", f"Car #{latest_leader.get('driver_number')}")

            except Exception as e:
                print(f"F1 Ingestion error: {e}")
                
            await asyncio.sleep(5)

# async def start_football_ingestion(session_id: str, api_match_id: str):
#     """Stub ready for API-Football integration."""
#     pass

# async def start_cricket_ingestion(session_id: str, api_match_id: str):
#     """Stub ready for Cricket API integration."""
#     pass