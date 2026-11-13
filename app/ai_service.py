import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

def get_answer(query: str, state: dict, logs: list) -> str:
    system_context = f"""
    You are an expert, concise sports commentator.
    CURRENT MATCH STATE: {state}
    RECENT EVENTS: {logs}
    Answer the user's question based strictly on this context. Keep it under 2 sentences.
    """
    response = model.generate_content(f"{system_context}\nUSER QUESTION: {query}")
    return response.text