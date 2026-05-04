import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from typing import List, Dict, Any

# ---------------- APP SETUP ----------------
app = FastAPI(title="Dental AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# ---------------- STATIC TREATMENTS DB ----------------
TREATMENTS = {
    "dental crowns": {
        "publicId": "01960000-0000-7000-8000-000000000107",
        "name": "Dental Crowns",
        "description": "Tooth-shaped cap placed over a damaged tooth to restore its shape and strength."
    },
    "dental implants": {
        "publicId": "01960000-0000-7000-8000-000000000105",
        "name": "Dental Implants",
        "description": "Surgical component that interfaces with the bone of the jaw or skull."
    },
    "fillings": {
        "publicId": "01960000-0000-7000-8000-000000000106",
        "name": "Fillings",
        "description": "Restoration of lost tooth structure using materials such as composite or amalgam."
    },
    "orthodontics": {
        "publicId": "01960000-0000-7000-8000-000000000100",
        "name": "Orthodontics",
        "description": "Braces, aligners, and jaw correction procedures."
    },
    "pediatric dentistry": {
        "publicId": "01960000-0000-7000-8000-000000000103",
        "name": "Pediatric Dentistry",
        "description": "Oral health care for children from infancy through the teen years."
    },
    "root canal": {
        "publicId": "01960000-0000-7000-8000-000000000101",
        "name": "Root Canal",
        "description": "Endodontic therapy to treat infection at the centre of a tooth."
    },
    "scaling and polishing": {
        "publicId": "01960000-0000-7000-8000-000000000104",
        "name": "Scaling and Polishing",
        "description": "Deep cleaning to remove plaque and tartar buildup."
    },
    "teeth whitening": {
        "publicId": "01960000-0000-7000-8000-000000000109",
        "name": "Teeth Whitening",
        "description": "Cosmetic procedure to lighten teeth and remove stains and discoloration."
    },
    "tooth extraction": {
        "publicId": "01960000-0000-7000-8000-000000000102",
        "name": "Tooth Extraction",
        "description": "Removal of a tooth from its socket in the bone."
    },
    "veneers": {
        "publicId": "01960000-0000-7000-8000-000000000108",
        "name": "Veneers",
        "description": "Thin shells of porcelain or composite resin bonded to the front of teeth."
    }
}

# ---------------- MEMORY ----------------
current_diagnosis = {
    "diagnosis_status": "pending",
    "diagnosis": []
}

# ---------------- SCHEMAS ----------------
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[Message]

# ---------------- CHAT ENDPOINT ----------------
@app.post("/chat")
async def chat(request: ChatRequest):
    global current_diagnosis

    try:
        history_formatted = [
            {"role": m.role, "parts": [{"text": m.content}]}
            for m in request.history
        ]

        system_instruction = """
You are a dental AI assistant.
IMPORTANT RULES:
1. You MUST choose CaseTypeId ONLY from this list:
- Dental Crowns
- Dental Implants
- Fillings
- Orthodontics
- Pediatric Dentistry
- Root Canal
- Scaling and Polishing
- Teeth Whitening
- Tooth Extraction
- Veneers
2. Always respond in JSON ONLY:
{
  "reply": "...",
  "diagnosis_status": "pending" or "completed",
  "diagnosis": [
    {
      "tooth_number": [int],
      "CaseTypeId": "string"
    }
  ]
}
3. Do NOT invent new CaseTypeId.
4. Ask one question at a time.
5. Be medical and careful.
"""

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=history_formatted,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json"
            }
        )

        data = json.loads(response.text)

        # ---------------- MAP AI OUTPUT -> CONTROLLED DATA ----------------
        mapped = []

        for d in data.get("diagnosis", []):
            case = d.get("CaseTypeId", "").strip().lower()

            if case in TREATMENTS:
                mapped.append({
                    "tooth_number": d.get("tooth_number", []),
                    **TREATMENTS[case]
                })

        data["diagnosis"] = mapped

        # ---------------- STATUS HANDLING ----------------
        if data.get("diagnosis_status") == "completed":
            current_diagnosis = {
                "diagnosis_status": "completed",
                "diagnosis": mapped
            }
            data["show_side_panel"] = True
            data["reply"] += " ألف سلامة عليك! الدكتور هيتواصل معاك قريب 😊🦷"
        else:
            data["show_side_panel"] = False

        return data

    except Exception as e:
        if "429" in str(e) or "503" in str(e):
            return {
                "reply": "السيرفر عليه ضغط دلوقتي، جرب بعد دقيقة 😊",
                "diagnosis_status": "pending",
                "show_side_panel": False,
                "diagnosis": []
            }

        raise HTTPException(status_code=500, detail=str(e))


# ---------------- GET DIAGNOSIS ----------------
@app.get("/diagnosis")
async def get_diagnosis():
    return {
        "success": True,
        "message": "Success",
        "data": current_diagnosis,
        "statusCode": 200,
        "warnings": None,
        "error": None,
        "links": None
    }
