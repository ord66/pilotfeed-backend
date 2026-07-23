from fastapi import FastAPI
from pydantic import BaseModel
import os
from google import genai
from google.genai import types

app = FastAPI()

# Model ismi ve API Key ortam değişkenlerinden dinamik okunur
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash").strip()

class EvaluationRequest(BaseModel):
    aircraft_type: str
    scenario_title: str
    selected_option: str
    is_correct: bool
    requires_cross_ref: bool

@app.get("/")
def home():
    return {"status": "Feed The Pilot Engine Active", "model_in_use": MODEL_NAME}

@app.post("/evaluate")
def evaluate_decision(req: EvaluationRequest):
    if not GEMINI_API_KEY:
        return {
            "status": "FAIL",
            "feedback": "Sistem Hatası: Yapay zeka servis yapılandırması eksik (API Key bulunamadı)."
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

    try:
        # Yeni SDK Client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2 # Havacılık analizinde tutarlılık için düşük sıcaklık
            ),
        )

        analysis = response.text.strip() if response.text else "Analiz oluşturulamadı, lütfen tekrar deneyin."

        return {
            "status": "SUCCESS" if req.is_correct else "FAIL",
            "feedback": analysis
        }

    except Exception as e:
        # Teknik hatayı loglar, istemciye (Swift) temiz fallback döner
        print(f"CRITICAL API ERROR: {str(e)}")
        return {
            "status": "FAIL",
            "feedback": "Değerlendirme servisine ulaşılamadı. Lütfen internet bağlantınızı ve sistem durumunu kontrol edin."
        }
