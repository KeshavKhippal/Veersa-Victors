"""
MedAuth Sentinel — Demo Runner
Runs all 3 demo scenarios and prints a formatted report.
Usage: python demo_runner.py (from medauth-sentinel root)
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))

from backend.orchestrator import run_prior_auth

scenarios = [
    {
        "name": "SCENARIO A — Clean Approval",
        "request": {
            "patient_id": "P001",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.9",
            "requesting_doctor": "Dr. Mehta"
        }
    },
    {
        "name": "SCENARIO B — Denial (No Metformin)",
        "request": {
            "patient_id": "P005",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.9",
            "requesting_doctor": "Dr. Singh"
        }
    },
    {
        "name": "SCENARIO C — Critic Override (MONEY SHOT)",
        "request": {
            "patient_id": "P010",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.65",
            "requesting_doctor": "Dr. Sharma"
        }
    }
]


def main():
    print("=" * 60)
    print("  MedAuth Sentinel — Demo Runner")
    print("  Running all 3 scenarios through the full agent pipeline")
    print("=" * 60)

    for i, scenario in enumerate(scenarios):
        print(f"\n{'=' * 60}")
        print(f"  {scenario['name']}")
        print(f"{'=' * 60}")
        print(f"  Request: {json.dumps(scenario['request'])}")
        print(f"  Processing...\n")

        try:
            result = run_prior_auth(scenario["request"])

            decision = result.get("final_decision", "ERROR")
            confidence = result.get("confidence", 0)
            revision = result.get("revision_made", False)
            trace_len = len(result.get("trace", []))
            reasoning = result.get("reasoning", [])
            critic = result.get("critic_feedback", {})

            print(f"  Final Decision:    {decision}")
            print(f"  Confidence:        {round(confidence * 100)}%")
            print(f"  Revision Made:     {'YES ⚡' if revision else 'NO'}")
            print(f"  Trace Steps:       {trace_len}")
            if reasoning:
                print(f"  Reasoning:         {reasoning[0][:80]}...")
            print(f"  Critic Agreed:     {'YES' if critic.get('agrees', True) else 'NO'}")

        except Exception as e:
            print(f"  ERROR: {str(e)}")

    print(f"\n{'=' * 60}")
    print("  Demo Runner Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
