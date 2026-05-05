"""
IntakeAgent — Validates incoming prior authorization requests.
Uses Groq (llama-3.3-70b-versatile) to validate PA requests.
Prompt loaded from prompts/intake_agent.yaml.
"""

import os
import json
import yaml
from dotenv import load_dotenv
from groq import Groq
from backend.tools.patient_lookup import get_patient


class IntakeAgent:
    def __init__(self):
        load_dotenv()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "prompts", "intake_agent.yaml"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_config = yaml.safe_load(f)
        self.system_prompt = self.prompt_config["system_prompt"]

    def run(self, request: dict) -> dict:
        """Validate an incoming PA request.

        Args:
            request: dict with patient_id, drug_requested, diagnosis_code, requesting_doctor

        Returns:
            dict with valid, patient_found, issues, validated_fields, intake_summary
        """
        patient_result = get_patient(request.get("patient_id", ""))
        patient_found = "error" not in patient_result

        user_message = f"""CURRENT REQUEST:
{json.dumps(request, indent=2)}

PATIENT LOOKUP RESULT:
Patient found: {patient_found}
{json.dumps(patient_result, indent=2)}"""

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
                max_tokens=1000,
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
                "valid": False,
                "patient_found": patient_found,
                "issues": ["Agent response parsing failed"],
                "raw_response": response_text
            }
        except Exception as e:
            return {
                "valid": False,
                "patient_found": False,
                "issues": [f"Agent error: {str(e)}"],
                "raw_response": str(e)
            }
