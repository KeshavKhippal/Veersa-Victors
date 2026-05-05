"""
History Checker Tool — Looks up prior authorization history from JSON.
No AI calls. Pure data retrieval for checking past PA decisions.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def get_prior_auth_history(patient_id: str) -> list:
    """Load data/prior_auths.json, return all records for this patient_id.
    Sort by date descending (most recent first). If none, return []"""
    filepath = os.path.join(DATA_DIR, "prior_auths.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            auths = json.load(f)
        patient_auths = [a for a in auths if a["patient_id"] == patient_id]
        patient_auths.sort(key=lambda x: x.get("date", ""), reverse=True)
        return patient_auths
    except FileNotFoundError:
        return []


def get_last_auth_for_drug(patient_id: str, drug_name: str) -> dict:
    """Return the most recent prior auth for this patient + drug combination.
    If none found, return {}"""
    filepath = os.path.join(DATA_DIR, "prior_auths.json")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            auths = json.load(f)
        matching = [
            a for a in auths
            if a["patient_id"] == patient_id and a["drug_requested"].lower() == drug_name.lower()
        ]
        if not matching:
            return {}
        matching.sort(key=lambda x: x.get("date", ""), reverse=True)
        return matching[0]
    except FileNotFoundError:
        return {}
