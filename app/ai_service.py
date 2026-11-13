from google import genai
import os
from typing import Dict, List

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "test_key"))

def get_answer(user_query: str, current_state: Dict, recent_logs: List) -> str:
    sport = current_state.get("sport", "Sports")
    
    system_context = f"""
    You are an expert, concise {sport} commentator and stadium assistant.
    CURRENT MATCH STATE: {current_state}
    RECENT EVENTS: {recent_logs}
    Answer the user's question based strictly on this context. 
    Keep it under 2 sentences. Do not hallucinate external events.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_context}\nUSER QUESTION: {user_query}"
        )
        return response.text
    except Exception as e:
        return f"AI Generation Error: {str(e)}"