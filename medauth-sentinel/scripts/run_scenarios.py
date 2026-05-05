"""
MedAuth Sentinel — Demo Scenario Runner
Runs all 4 test scenarios and prints a formatted report.
Use this before your presentation to verify everything works.

Usage: python run_scenarios.py
Note: Needs Groq API key in .env and data files in /data
"""

import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.orchestrator import run_prior_auth

SCENARIOS = [
    {
        "id": "A",
        "name": "Clean Approval",
        "desc": "P001 + Ozempic — T2DM diagnosed + Metformin history → APPROVE",
        "request": {
            "patient_id": "P001",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.9",
            "requesting_doctor": "Dr. Mehta"
        },
        "expected": "APPROVED"
    },
    {
        "id": "B",
        "name": "Denial — No Prior Drug",
        "desc": "P005 + Ozempic — T2DM but NO Metformin history → DENY",
        "request": {
            "patient_id": "P005",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.9",
            "requesting_doctor": "Dr. Singh"
        },
        "expected": "DENIED"
    },
    {
        "id": "C",
        "name": "Critic Override — DEMO MONEY SHOT",
        "desc": "P010 + E11.65 variant — Critic catches missed exception → APPROVE",
        "request": {
            "patient_id": "P010",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.65",
            "requesting_doctor": "Dr. Sharma"
        },
        "expected": "APPROVED"
    },
    {
        "id": "D",
        "name": "Invalid Patient — Intake Rejection",
        "desc": "P999 does not exist — pipeline stops at intake",
        "request": {
            "patient_id": "P999",
            "drug_requested": "Ozempic",
            "diagnosis_code": "E11.9",
            "requesting_doctor": "Dr. Test"
        },
        "expected": "REJECTED"
    }
]

def run_all():
    print("\n" + "═" * 62)
    print("  MedAuth Sentinel — Demo Scenario Runner")
    print("  Running 4 scenarios. Takes approximately 2 minutes.")
    print("═" * 62)

    results = []
    total_start = time.time()

    for scenario in SCENARIOS:
        print(f"\n{'─' * 62}")
        print(f"  SCENARIO {scenario['id']}: {scenario['name']}")
        print(f"  {scenario['desc']}")
        print(f"{'─' * 62}")
        print("  ⏳ Running pipeline...")

        start = time.time()
        try:
            result = run_prior_auth(scenario["request"])
            duration = int((time.time() - start) * 1000)

            decision   = result.get("final_decision", "ERROR")
            confidence = result.get("confidence", 0)
            revision   = result.get("revision_made", False)
            changed    = result.get("decision_changed", False)
            steps      = len(result.get("trace", []))
            status     = result.get("status", "UNKNOWN")

            expected = scenario["expected"]
            if expected == "REJECTED":
                passed = status == "REJECTED_AT_INTAKE"
            else:
                passed = decision == expected

            icon = "✅" if passed else "⚠️ "

            print(f"\n  {icon} Status:           {status}")
            print(f"     Final Decision:   {decision}")
            print(f"     Confidence:       {confidence * 100:.1f}%")
            print(f"     Revision Made:    {'YES ⚡' if revision else 'NO'}")
            print(f"     Decision Changed: {'YES' if changed else 'NO'}")
            print(f"     Trace Steps:      {steps}")
            print(f"     Duration:         {duration}ms")

            reasoning = result.get("reasoning", [])
            if reasoning:
                print(f"\n     Reasoning summary:")
                print(f"       → {reasoning[0]}")

            critic = result.get("critic_feedback", {})
            if critic:
                print(f"\n     Critic:")
                print(f"       Agrees: {critic.get('agrees')} | "
                      f"Severity: {critic.get('severity')}")
                issues = critic.get("issues_found", [])
                if issues:
                    print(f"       Issue: {issues[0]}")

            results.append({
                "id":       scenario["id"],
                "name":     scenario["name"],
                "decision": decision,
                "revision": revision,
                "changed":  changed,
                "steps":    steps,
                "passed":   passed,
                "duration": duration
            })

        except Exception as e:
            print(f"\n  ❌ SCENARIO CRASHED: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "id":       scenario["id"],
                "name":     scenario["name"],
                "decision": "ERROR",
                "revision": False,
                "changed":  False,
                "steps":    0,
                "passed":   False,
                "duration": 0
            })

    total_time = int(time.time() - total_start)
    all_passed = all(r["passed"] for r in results)

    print(f"\n{'═' * 62}")
    print("  FINAL SUMMARY")
    print(f"{'═' * 62}")

    for r in results:
        icon         = "✅" if r["passed"] else "⚠️ "
        override_tag = " ⚡ CRITIC OVERRIDE" if r["revision"] else ""
        print(f"  {icon} Scenario {r['id']}: "
              f"{r['decision']:<28}"
              f"Steps: {r['steps']}"
              f"{override_tag}")

    print(f"\n  All scenarios passed: {'✅ YES' if all_passed else '⚠️  CHECK ABOVE'}")
    print(f"  Total time: {total_time}s")

    override_happened = any(r["revision"] for r in results)
    if override_happened:
        print(f"\n  ⚡ CRITIC OVERRIDE triggered!")
        print(f"     This is your demo money shot.")
        print(f"     Show the trace with 4 steps during presentation.")
    else:
        print(f"\n  ℹ️  No critic override this run.")
        print(f"     If Scenario C decision is APPROVED, that is still correct.")
        print(f"     It means DecisionAgent caught E11.65 on the first pass.")

    print(f"{'═' * 62}\n")
    return all_passed


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
