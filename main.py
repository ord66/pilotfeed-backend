from fastapi import FastAPI
from pydantic import BaseModel
import os
import google.generativeai as genai

app = FastAPI()

# Render Environment Variables altından GEMINI_API_KEY okunur
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class EvaluationRequest(BaseModel):
    aircraft_type: str
    scenario_title: str
    selected_option: str
    is_correct: bool
    requires_cross_ref: bool

@app.get("/")
def home():
    return {"status": "Feed The Pilot Gemini Engine Active"}

@app.post("/evaluate")
def evaluate_decision(req: EvaluationRequest):
    if not GEMINI_API_KEY:
        return {
            "status": "FAIL",
            "feedback": "HATA: GEMINI_API_KEY Render paneline eklenmemiş veya okunamıyor."
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

    # Tamamen ÜCRETSİZ katmanda çalışan modeller (Öncelik Sırası)
    candidate_models = [
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-pro",
        "gemini-2.5-flash"
    ]


    selected_model_name = None

    # Hesabınızda desteklenen ilk çalışan modeli bulalım
    try:
        available_models = [
            m.name.replace("models/", "") 
            for m in genai.list_models() 
            if "generateContent" in m.supported_generation_methods
        ]
        
        for candidate in candidate_models:
            if candidate in available_models:
                selected_model_name = candidate
                break
        
        # Eğer listeden eşleşen çıkmazsa desteklenen ilk modeli seç
        if not selected_model_name and available_models:
            selected_model_name = available_models[0]

    except Exception:
        # Liste çekilemezse varsayılan model adı dene
        selected_model_name = "gemini-2.5-flash"

    try:
        model = genai.GenerativeModel(
            model_name=selected_model_name,
            system_instruction=system_instruction
        )
        
        response = model.generate_content(user_prompt)
        
        if response and hasattr(response, 'text') and response.text:
            analysis = response.text.strip()
        else:
            analysis = "LLM yanıt üretti ancak boş döndü."

    except Exception as e:
        analysis = f"Gemini API Hatası ({selected_model_name}): {str(e)}"

    return {
        "status": "SUCCESS" if req.is_correct else "FAIL",
        "feedback": analysis
    }
