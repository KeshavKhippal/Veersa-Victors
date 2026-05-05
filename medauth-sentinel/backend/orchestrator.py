"""
Orchestrator — runs agents in sequence with critic loop.
This is the brain of MedAuth Sentinel.

Flow:
  1. IntakeAgent validates the request
  2. DecisionAgent makes the initial decision
  3. CriticAgent reviews the decision
  4. If critic disagrees → DecisionAgent runs again with critic feedback
"""

from backend.agents.intake_agent import IntakeAgent
from backend.agents.decision_agent import DecisionAgent
from backend.agents.critic_agent import CriticAgent


def run_prior_auth(request: dict) -> dict:
    """Run the full prior authorization pipeline.

    Args:
        request: dict with patient_id, drug_requested, diagnosis_code, requesting_doctor

    Returns:
        dict with status, final_decision, confidence, reasoning, trace, etc.
    """
    trace = []  # every agent step gets appended here

    intake_agent = IntakeAgent()
    intake_result = intake_agent.run(request)
    trace.append({
        "step": 1,
        "agent": "IntakeAgent",
        "status": "completed",
        "output": intake_result
    })

    if not intake_result.get("valid", False):
        return {
            "status": "REJECTED_AT_INTAKE",
            "final_decision": "REJECTED",
            "reason": "Request failed intake validation",
            "issues": intake_result.get("issues", []),
            "trace": trace,
            "request": request
        }

    decision_agent = DecisionAgent()
    decision_result = decision_agent.run(request)
    trace.append({
        "step": 2,
        "agent": "DecisionAgent",
        "status": "completed",
        "output": decision_result
    })

    critic_agent = CriticAgent()
    critic_result = critic_agent.run(request, decision_result)
    trace.append({
        "step": 3,
        "agent": "CriticAgent",
        "status": "completed",
        "output": critic_result
    })

    final_decision = decision_result
    revision_made = False

    if not critic_result.get("agrees", True) and critic_result.get("severity") in ["minor", "major"]:
        revised_result = decision_agent.run(request, critic_feedback=critic_result)
        trace.append({
            "step": 4,
            "agent": "DecisionAgent_Revised",
            "status": "completed",
            "note": "Revised after critic feedback",
            "output": revised_result
        })
        final_decision = revised_result
        revision_made = True

    return {
        "status": "COMPLETED",
        "final_decision": final_decision.get("decision", "ERROR"),
        "confidence": final_decision.get("confidence", 0),
        "reasoning": final_decision.get("reasoning", []),
        "criteria_met": final_decision.get("criteria_met", {}),
        "critic_feedback": critic_result,
        "revision_made": revision_made,
        "intake_summary": intake_result.get("intake_summary", ""),
        "trace": trace,
        "request": request
    }
