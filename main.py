from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests

app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

class EvaluationRequest(BaseModel):
    aircraft_type: str
    scenario_title: str
    selected_option: str
    is_correct: bool
    requires_cross_ref: bool

@app.get("/")
def home():
    return {"status": "Feed The Pilot API Running"}

@app.post("/evaluate")
def evaluate_decision(req: EvaluationRequest):
    system_prompt = (
        "Sen tecrübeli bir uçuş emniyet ve kaza inceleme uzmanısın (NTSB/EASA). "
        "Pilotun acil durum kararını analiz edip kısa, teknik açıdan doğru ve öğretici bir geri bildirim ver."
    )

    user_prompt = f"""
    Uçak Tipi: {req.aircraft_type}
    Acil Durum: {req.scenario_title}
    Pilotun Kararı: {req.selected_option}
    Doğru Seçim mi?: {req.is_correct}
    Çapraz Referans (QRH) İhtiyacı Atlandı mı?: {req.requires_cross_ref and not req.is_correct}

    Lütfen bu kararı 2-3 cümle ile değerlendir. Emniyet riskini veya doğru hamlenin nedenini belirt.
    """

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        res_data = response.json()
        analysis = res_data['choices'][0]['message']['content']
    except Exception as e:
        analysis = "LLM Analizi oluşturulamadı. Karar kaydedildi."

    return {
        "status": "SUCCESS" if req.is_correct else "FAIL",
        "feedback": analysis
    }
