from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# Render üzerindeki GEMINI_API_KEY okunur
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

class EvaluationRequest(BaseModel):
    aircraft_type: str
    scenario_title: str
    selected_option: str
    is_correct: bool
    requires_cross_ref: bool

@app.get("/")
def home():
    return {"status": "Feed The Pilot API Direct REST Active"}

@app.post("/evaluate")
def evaluate_decision(req: EvaluationRequest):
    if not GEMINI_API_KEY:
        return {
            "status": "FAIL",
            "feedback": "HATA: GEMINI_API_KEY Render paneline eklenmemiş."
        }

    system_instruction = (
        "Sen tecrübeli bir A320 Check Captain ve NTSB/EASA Kaza İnceleme Uzmanısın. "
        "Uçuş simülasyonunda pilotun yaptığı acil durum seçimlerini analiz ediyorsun. "
        "Airbus FCOM/QRH prosedürlerine bağlı kalarak, kararın emniyet risklerini, "
        "varsa atlanan QRH Memory Items çapraz referanslarını ve teknik nedenlerini "
        "kısa, vurucu ve öğretici 2-3 cümle ile Türkçe olarak açıkla."
    )

    user_prompt = f"""
    Uçak Tipi: {req.aircraft_type}
    Acil Durum Senaryosu: {req.scenario_title}
    Pilotun Kararı: {req.selected_option}
    Doğru Seçim mi?: {req.is_correct}
    Atlanan QRH Çapraz Referansı Var mı?: {req.requires_cross_ref and not req.is_correct}

    Lütfen bu hamleyi uçuş emniyeti ve sistem mantığı (Antiskid, N/W Steering, Decel Light) açısından değerlendir.
    """

    # Doğrudan Google v1 REST API Uç Noktası
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        res_data = response.json()

        if response.status_code == 200:
            analysis = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            error_msg = res_data.get("error", {}).get("message", "Bilinmeyen API Hatası")
            analysis = f"Google API Hatası ({response.status_code}): {error_msg}"

    except Exception as e:
        analysis = f"Sunucu Bağlantı Hatası: {str(e)}"

    return {
        "status": "SUCCESS" if req.is_correct else "FAIL",
        "feedback": analysis
    }
