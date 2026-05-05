"""
CriticAgent — Adversarially reviews DecisionAgent output.
Uses Groq (llama-3.3-70b-versatile) to find flaws in reasoning.
Prompt loaded from prompts/critic_agent.yaml.
"""

import os
import json
import yaml
from dotenv import load_dotenv
from groq import Groq
from backend.tools.patient_lookup import get_patient_full_profile
from backend.tools.policy_checker import get_policy_for_drug


class CriticAgent:
    def __init__(self):
        load_dotenv()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "critic_agent.yaml"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_config = yaml.safe_load(f)
        self.system_prompt = self.prompt_config["system_prompt"]

    def run(self, request: dict, decision_result: dict) -> dict:
        """Adversarially review a decision from the DecisionAgent.

        Args:
            request: dict with patient_id, drug_requested, diagnosis_code, requesting_doctor
            decision_result: dict output from DecisionAgent.run()

        Returns:
            dict with agrees, severity, issues_found, specific_flags, suggested_revision, critic_summary
        """
        patient_profile = get_patient_full_profile(request.get("patient_id", ""))

        payer = patient_profile.get("patient", {}).get("payer", "")
        policy = get_policy_for_drug(payer, request.get("drug_requested", ""))

        user_message = f"""ORIGINAL REQUEST:
{json.dumps(request, indent=2)}

PATIENT PROFILE:
{json.dumps(patient_profile, indent=2)}

PAYER POLICY:
{json.dumps(policy, indent=2)}

DECISION TO REVIEW:
{json.dumps(decision_result, indent=2)}"""

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
                "agrees": True,
                "severity": "none",
                "issues_found": ["Critic response parsing failed"],
                "specific_flags": {},
                "suggested_revision": None,
                "critic_summary": "Critic could not parse response",
                "raw_response": response_text
            }
        except Exception as e:
            return {
                "agrees": True,
                "severity": "none",
                "issues_found": [f"Critic error: {str(e)}"],
                "specific_flags": {},
                "suggested_revision": None,
                "critic_summary": f"Critic encountered error: {str(e)}",
                "raw_response": str(e)
            }
