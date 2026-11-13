import asyncio
import httpx
from app.state_manager import state_manager

# OpenF1 Free Tier Base URL
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
    """Specific ingestor for F1 with optimized chronological polling."""
    last_rc_date = None
    last_pos_date = None
    current_driver_positions = {}
    sport = "Formula 1"
    
    # Increased timeout to 30s to safely handle the first large payload
    async with httpx.AsyncClient(timeout=30.0) as client:
        f1_session_key = await fetch_latest_f1_session_key(client)
        state_manager.update_state(session_id, sport, "session_key", f1_session_key)
        
        # 1. Fetch Driver Mappings
        driver_map = {}
        try:
            drv_resp = await client.get(f"{F1_BASE_URL}/drivers?session_key={f1_session_key}")
            if drv_resp.status_code == 200:
                for d in drv_resp.json():
                    driver_map[d.get('driver_number')] = {
                        "name": d.get('full_name', d.get('name_acronym', f"Car {d.get('driver_number')}")),
                        "team": d.get('team_name', 'Unknown Team')
                    }
        except Exception:
            pass

        state_manager.add_log(session_id, sport, f"Connected to OpenF1 Live API. Session: {f1_session_key}")

        while True:
            try:
                # 2. Race Control Logic
                rc_url = f"{F1_BASE_URL}/race_control?session_key={f1_session_key}"
                if last_rc_date:
                    rc_url += f"&date>{last_rc_date}"
                    
                rc_resp = await client.get(rc_url)
                if rc_resp.status_code == 200:
                    messages = sorted(rc_resp.json(), key=lambda x: x.get('date', ''))
                    for msg in messages:
                        flag = msg.get('flag', '')
                        state_manager.add_log(session_id, sport, f"[RACE CONTROL] {flag} - {msg.get('message', '')}".strip(" -"))
                        if flag:
                            state_manager.update_state(session_id, sport, "flags", flag)
                        last_rc_date = msg.get('date')

                # 3. Live Standings Logic
                pos_url = f"{F1_BASE_URL}/position?session_key={f1_session_key}"
                if last_pos_date:
                    pos_url += f"&date>{last_pos_date}"
                    
                pos_resp = await client.get(pos_url)
                if pos_resp.status_code == 200:
                    positions = sorted(pos_resp.json(), key=lambda x: x.get('date', ''))
                    
                    if positions:
                        for p in positions:
                            current_driver_positions[p.get('driver_number')] = p.get('position')
                            last_pos_date = p.get('date')
                        
                       
                        standings = []
                        
                        # Standard F1 points for Top 10
                        points_system = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
                        
                        for d_num, pos in current_driver_positions.items():
                            info = driver_map.get(d_num, {"name": f"Car {d_num}", "team": "Unknown Team"})
                            
                            # Assign points if they are in the Top 10, otherwise 0
                            live_points = points_system.get(pos, 0)
                            
                            standings.append({
                                "pos": pos,
                                "driver": info["name"],
                                "team": info["team"],
                                "points": live_points
                            })
                        
                        # Sort by track position
                        standings = sorted(standings, key=lambda x: x['pos'])
                        
                        state_manager.update_state(session_id, sport, "standings", standings)
                        if standings:
                            state_manager.update_state(session_id, sport, "leader", standings[0]['driver'])

            except Exception as e:
                print(f"F1 Ingestion error: {e}")
                
            await asyncio.sleep(8)