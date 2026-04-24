from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Dental Chat API", version="1.0")

# =========================
# STATE INIT
# =========================
def start_state():
    return {
        "mode": None,
        "answers": {},
        "asked": [],
        "current_q": "mode"
    }

# =========================
# QUESTIONS
# =========================
MODE_QUESTION = "عايز ايه؟ (تشخيص / تجميل / علاج)"

DIAGNOSIS_Q = {
    "pain": "هل عندك وجع في السنان؟",
    "bleeding": "هل في نزيف؟",
    "swelling": "هل في تورم؟",
    "sensitivity": "هل في حساسية؟"
}

COSMETIC_Q = {
    "whitening": "عايز تبييض؟",
    "braces": "مهتم بالتقويم؟",
    "cleaning": "عايز تنظيف جير؟"
}

TREATMENT_Q = {
    "extract": "عايز خلع سن؟",
    "filling": "محتاج حشو؟",
    "implant": "عايز زرع سن؟"
}

# =========================
class ChatRequest(BaseModel):
    answer: str
    state: dict | None = None

# =========================
def generate_diagnosis(state):
    a = state["answers"]

    if a.get("pain") == "اه" and a.get("swelling") == "اه":
        return {"diagnosis": "خراج"}

    if a.get("bleeding") == "اه":
        return {"diagnosis": "التهاب لثة"}

    if a.get("pain") == "اه":
        return {"diagnosis": "تسوس"}

    return {"diagnosis": "سليم"}

# =========================
@app.get("/start")
def start():
    return {
        "question": MODE_QUESTION,
        "state": start_state()
    }

# =========================
@app.post("/chat")
def chat(req: ChatRequest):

    state = req.state or start_state()
    answer = req.answer.strip()

    # =========================
    # MODE SELECTION
    # =========================
    if state["mode"] is None:

        if answer in ["تشخيص", "diagnosis"]:
            state["mode"] = "diagnosis"
            state["current_q"] = "pain"

        elif answer in ["تجميل", "cosmetic"]:
            state["mode"] = "cosmetic"
            state["current_q"] = "whitening"

        elif answer in ["علاج", "treatment"]:
            state["mode"] = "treatment"
            state["current_q"] = "extract"

        else:
            return {
                "done": False,
                "question": MODE_QUESTION,
                "state": state
            }

        q = state["current_q"]
        question_map = {
            "diagnosis": DIAGNOSIS_Q,
            "cosmetic": COSMETIC_Q,
            "treatment": TREATMENT_Q
        }

        return {
            "done": False,
            "question": question_map[state["mode"]][q],
            "state": state
        }

    # =========================
    # SAVE ANSWER
    # =========================
    q = state["current_q"]
    state["answers"][q] = answer
    state["asked"].append(q)

    # =========================
    # FLOW HANDLER
    # =========================
    flow_map = {
        "diagnosis": DIAGNOSIS_Q,
        "cosmetic": COSMETIC_Q,
        "treatment": TREATMENT_Q
    }

    flow = flow_map[state["mode"]]

    # END CONDITION
    if len(state["asked"]) >= len(flow):
        if state["mode"] == "diagnosis":
            return {
                "done": True,
                "result": generate_diagnosis(state),
                "state": state
            }

        return {
            "done": True,
            "result": {
                "type": state["mode"],
                "answers": state["answers"]
            },
            "state": state
        }

    # NEXT QUESTION
    for key in flow:
        if key not in state["asked"]:
            state["current_q"] = key
            return {
                "done": False,
                "question": flow[key],
                "state": state
            }