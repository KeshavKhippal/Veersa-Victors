"""
DecisionAgent — Makes the core prior authorization decision.
Uses Groq (llama-3.3-70b-versatile) to evaluate clinical and policy data.
Prompt loaded from prompts/decision_agent.yaml.
"""

import os
import json
import yaml
from dotenv import load_dotenv
from groq import Groq
from backend.tools.patient_lookup import get_patient_full_profile
from backend.tools.policy_checker import get_policy_for_drug
from backend.tools.history_checker import get_prior_auth_history


class DecisionAgent:
    def __init__(self):
        load_dotenv()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "decision_agent.yaml"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_config = yaml.safe_load(f)
        self.system_prompt = self.prompt_config["system_prompt"]

    def run(self, request: dict, critic_feedback: dict = None) -> dict:
        """Make a PA decision based on patient data, policy rules, and history.

        Args:
            request: dict with patient_id, drug_requested, diagnosis_code, requesting_doctor
            critic_feedback: optional dict from CriticAgent if this is a revision

        Returns:
            dict with decision, confidence, reasoning, criteria_met, missing_info
        """
        patient_profile = get_patient_full_profile(request.get("patient_id", ""))

        payer = patient_profile.get("patient", {}).get("payer", "")
        policy = get_policy_for_drug(payer, request.get("drug_requested", ""))

        history = get_prior_auth_history(request.get("patient_id", ""))

        # Build policy section — handle web search results specially
        policy_section = ""
        if policy.get("action_required") == "AGENT_MECHANISM_CHECK":
            policy_section = f"""PAYER POLICY STATUS: Drug not found in policy database via name matching.
A real-time web search was conducted automatically.

{policy.get("web_search_summary", "No web search results available.")}

COVERED DRUGS FOR {policy.get("payer", "this payer")}:
{json.dumps(policy.get("covered_drugs_for_payer", []), indent=2)}

FULL PAYER POLICIES (for reference):
{json.dumps(policy.get("full_payer_policies", []), indent=2)}

INSTRUCTION: Use the web search results above to identify the 
requested drug's active ingredient and mechanism. Then determine 
if any covered drug shares the same molecule or mechanism.
"""
        else:
            policy_section = f"""PAYER POLICY FOR REQUESTED DRUG:
{json.dumps(policy, indent=2)}
"""

        user_message = f"""PATIENT PROFILE:
{json.dumps(patient_profile, indent=2)}

{policy_section}

PRIOR AUTHORIZATION HISTORY:
{json.dumps(history, indent=2)}

CURRENT REQUEST:
{json.dumps(request, indent=2)}"""

        if critic_feedback is not None:
            user_message += f"""

CRITIC FEEDBACK (you must address these issues in your revised decision):
{json.dumps(critic_feedback, indent=2)}"""

        additional_notes = request.get("additional_notes", "").strip()
        if additional_notes:
            user_message += f"""

ADDITIONAL CLINICAL NOTES FROM REQUESTING DOCTOR:
{additional_notes}

Consider this carefully. It may contain lab values, treatment history,
or medical necessity context not in the structured data above.
"""
        user_message += "\n\nRespond with ONLY the JSON object as specified."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=1500,
            )

            response_text = response.choices[0].message.content
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            return result

        except json.JSONDecodeError:
            return {
                "decision": "ERROR",
                "confidence": 0,
                "reasoning": ["Agent response parsing failed"],
                "criteria_met": {},
                "missing_info": [],
                "raw_response": response_text
            }
        except Exception as e:
            return {
                "decision": "ERROR",
                "confidence": 0,
                "reasoning": [f"Agent error: {str(e)}"],
                "criteria_met": {},
                "missing_info": [],
                "raw_response": str(e)
            }
