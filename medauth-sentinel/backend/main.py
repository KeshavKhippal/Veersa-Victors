"""
MedAuth Sentinel — FastAPI Main Application
Wraps the orchestrator and exposes it as a REST API.
Run: uvicorn backend.main:app --reload
"""

from typing import Optional
import json
import os
import subprocess
from contextlib import asynccontextmanager
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import PARequest, PromptUpdate, Clinician, Notification
from backend.orchestrator import run_prior_auth

MOCK_CLINICIAN = {
    "id": "DR001",
    "name": "Dr. Jameson",
    "role": "Chief Medical Officer",
    "avatar_color": "med-primary"
}

MOCK_NOTIFICATIONS = [
    {
        "id": "NOTIF001",
        "title": "Auth Decision",
        "message": "Case P001 Approved for Ozempic",
        "type": "success",
        "timestamp": "10:45 AM",
        "read": False
    },
    {
        "id": "NOTIF002",
        "title": "Policy Update",
        "message": "New prior-auth rules for GLP-1 agonists",
        "type": "info",
        "timestamp": "Yesterday",
        "read": True
    }
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup hook — runs before the server accepts requests.

    On Render (and other cloud platforms), the filesystem resets
    on each deploy. This hook auto-regenerates the synthetic data
    files if they are missing, so the app always has data to work with.
    """
    data_files = [
        "data/patients.json",
        "data/diagnoses.json",
        "data/medications.json",
        "data/payer_policies.json",
        "data/prior_auths.json"
    ]

    missing = [f for f in data_files if not os.path.exists(f)]

    if missing:
        print(f"[STARTUP] Missing data files: {missing}")
        print("[STARTUP] Auto-generating synthetic data...")
        try:
            result = subprocess.run(
                ["python", "backend/generate_data.py"],
                check=True,
                capture_output=True,
                text=True
            )
            print("[STARTUP] Data generation output:", result.stdout)
            print("[STARTUP] [OK] All data files generated successfully")
        except subprocess.CalledProcessError as e:
            print(f"[STARTUP] [ERROR] Data generation failed: {e}")
            print(f"[STARTUP] stderr: {e.stderr}")
    else:
        print(f"[STARTUP] [OK] All {len(data_files)} data files present")

    yield  # Server runs here

    print("[SHUTDOWN] MedAuth Sentinel shutting down gracefully")


app = FastAPI(
    title="MedAuth Sentinel API",
    description="Autonomous Prior Authorization & Appeals Agent — Veersa Hackathon 2026",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://medauth-sentinel-backend.onrender.com",
        "https://*.vercel.app",
        "https://*.onrender.com",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "MedAuth Sentinel API is running", "version": "1.0.0"}


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "agents": ["IntakeAgent", "DecisionAgent", "CriticAgent"]
    }


@app.post("/api/submit-request")
def submit_request(request: PARequest):
    try:
        result = run_prior_auth(request.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")


@app.get("/api/patients")
def get_patients():
    try:
        filepath = os.path.join(DATA_DIR, "patients.json")
        with open(filepath, "r", encoding="utf-8") as f:
            patients = json.load(f)
        return patients
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="patients.json not found")


@app.get("/api/prompts")
def get_prompts():
    prompts = {}
    for agent_name in ["intake_agent", "decision_agent", "critic_agent"]:
        try:
            filepath = os.path.join(PROMPTS_DIR, f"{agent_name}.yaml")
            with open(filepath, "r", encoding="utf-8") as f:
                prompts[agent_name] = yaml.safe_load(f)
        except FileNotFoundError:
            prompts[agent_name] = {"error": f"{agent_name}.yaml not found"}
    return prompts


@app.put("/api/prompts/{agent_name}")
def update_prompt(agent_name: str, update: PromptUpdate):
    valid_agents = ["intake_agent", "decision_agent", "critic_agent"]
    if agent_name not in valid_agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found. Valid: {valid_agents}")

    try:
        filepath = os.path.join(PROMPTS_DIR, f"{agent_name}.yaml")
        with open(filepath, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        config["system_prompt"] = update.system_prompt

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        return {
            "success": True,
            "agent": agent_name,
            "message": "Prompt updated successfully"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"{agent_name}.yaml not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating prompt: {str(e)}")


@app.get("/api/scenarios")
def get_scenarios():
    return [
        {
            "id": "scenario_a",
            "name": "Scenario A — Clean Approval",
            "description": "P001 requests Ozempic. Has T2DM + Metformin history. Should approve.",
            "request": {
                "patient_id": "P001",
                "drug_requested": "Ozempic",
                "diagnosis_code": "E11.9",
                "requesting_doctor": "Dr. Mehta"
            }
        },
        {
            "id": "scenario_b",
            "name": "Scenario B — Denial (No Prior Drug)",
            "description": "P005 requests Ozempic. Has T2DM but never tried Metformin. Should deny.",
            "request": {
                "patient_id": "P005",
                "drug_requested": "Ozempic",
                "diagnosis_code": "E11.9",
                "requesting_doctor": "Dr. Singh"
            }
        },
        {
            "id": "scenario_c",
            "name": "Scenario C — Critic Override (Demo Money Shot)",
            "description": "P010 has E11.65 (diabetes variant). Critic should catch that this is valid and override initial decision.",
            "request": {
                "patient_id": "P010",
                "drug_requested": "Ozempic",
                "diagnosis_code": "E11.65",
                "requesting_doctor": "Dr. Sharma"
            }
        }
    ]


@app.get("/api/user", response_model=Clinician)
def get_current_user():
    return MOCK_CLINICIAN


@app.get("/api/notifications", response_model=list[Notification])
def get_notifications():
    return MOCK_NOTIFICATIONS

