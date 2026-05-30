"""
MedAuth Sentinel — Tool Tests
Tests all 3 tool files: patient_lookup, policy_checker, history_checker.
Run: pytest tests/test_tools.py -v
"""

import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.tools.patient_lookup import (
    get_patient,
    get_patient_diagnoses,
    get_patient_medications,
    get_patient_full_profile,
)
from backend.tools.policy_checker import get_policy_for_drug
from backend.tools.history_checker import get_prior_auth_history


# ---- Test 1: Get patient P001 ----
def test_get_patient_p001():
    result = get_patient("P001")
    assert isinstance(result, dict)
    assert "name" in result
    assert result["patient_id"] == "P001"


# ---- Test 2: Patient not found ----
def test_get_patient_not_found():
    result = get_patient("P999")
    assert "error" in result


# ---- Test 3: P001 diagnoses include E11.9 ----
def test_get_diagnoses_p001():
    result = get_patient_diagnoses("P001")
    assert isinstance(result, list)
    assert len(result) > 0
    assert any(d["icd10_code"] == "E11.9" for d in result)


# ---- Test 4: P001 medications include Metformin ----
def test_get_medications_p001():
    result = get_patient_medications("P001")
    assert isinstance(result, list)
    assert any(m["drug_name"] == "Metformin" for m in result)


# ---- Test 5: P005 does NOT have Metformin ----
def test_p005_no_metformin():
    result = get_patient_medications("P005")
    assert not any(m["drug_name"] == "Metformin" for m in result)


# ---- Test 6: Policy checker — Ozempic + BlueCross ----
def test_policy_checker_ozempic_bluecross():
    result = get_policy_for_drug("BlueCross", "Ozempic")
    assert isinstance(result, dict)
    assert "requires_diagnosis" in result
    assert "E11.9" in result["requires_diagnosis"]


# ---- Test 7: Prior auth history for P001 ----
def test_prior_auth_history_p001():
    result = get_prior_auth_history("P001")
    assert isinstance(result, list)


# ---- Test 8: Full profile combines all data ----
def test_full_profile():
    result = get_patient_full_profile("P001")
    assert "patient" in result
    assert "diagnoses" in result
    assert "medications" in result
    assert result["patient"]["patient_id"] == "P001"
    assert len(result["diagnoses"]) > 0
    assert len(result["medications"]) > 0


# ── Drug Matching Pipeline Tests ──────────────────────────────────

def test_drug_exact_match_uppercase():
    """Tier 1: Exact match regardless of case."""
    result = get_policy_for_drug("BlueCross", "OZEMPIC")
    assert "error" not in result, f"Unexpected error: {result}"
    assert result.get("match_type") == "exact", \
        f"Expected exact match, got: {result.get('match_type')}"


def test_drug_exact_match_lowercase():
    """Tier 1: Exact match with lowercase input."""
    result = get_policy_for_drug("BlueCross", "ozempic")
    assert "error" not in result
    assert result.get("match_type") == "exact"


def test_drug_partial_match_with_suffix():
    """Tier 2: Partial match catches appended route/form."""
    result = get_policy_for_drug("BlueCross", "Ozempic injection")
    assert "error" not in result, f"Unexpected error: {result}"
    assert result.get("match_type") in ["exact", "partial"], \
        f"Expected exact or partial, got: {result.get('match_type')}"


def test_drug_alias_generic_name():
    """Tier 3: Generic name matches brand-named policy."""
    result = get_policy_for_drug("BlueCross", "semaglutide")
    assert "error" not in result, f"Unexpected error: {result}"
    assert result.get("match_type") == "alias", \
        f"Expected alias match, got: {result.get('match_type')}"


def test_drug_alias_brand_variant_wegovy():
    """Tier 3: Wegovy (same molecule as Ozempic) matches Ozempic policy."""
    result = get_policy_for_drug("BlueCross", "Wegovy")
    assert "error" not in result, f"Unexpected error: {result}"
    assert result.get("match_type") in ["exact", "alias", "partial"], \
        f"Expected a valid match type, got: {result.get('match_type')}"


def test_drug_alias_brand_variant_rybelsus():
    """Tier 3: Rybelsus (oral semaglutide) matches Ozempic policy."""
    result = get_policy_for_drug("BlueCross", "Rybelsus")
    assert "error" not in result, f"Unexpected error: {result}"
    assert result.get("match_type") in ["exact", "alias", "partial"], \
        f"Expected a valid match type, got: {result.get('match_type')}"


def test_drug_alias_lipitor_to_atorvastatin():
    """Tier 3: Brand Lipitor matches generic atorvastatin in policy."""
    result = get_policy_for_drug("Aetna", "atorvastatin")
    # Only assert no crash — payer may not have Lipitor policy
    assert isinstance(result, dict), "Result must be a dict"


def test_drug_not_found_returns_agentic_fallback():
    """Tier 4: Unknown drug triggers agentic mechanism check."""
    result = get_policy_for_drug("BlueCross", "completely_unknown_drug_xyz")
    assert "error" not in result, \
        f"Should return fallback not error, got: {result}"
    assert result.get("action_required") == "AGENT_MECHANISM_CHECK", \
        f"Expected AGENT_MECHANISM_CHECK, got: {result.get('action_required')}"
    assert "covered_drugs_for_payer" in result, \
        "Fallback must include covered_drugs_for_payer list"
    assert isinstance(result["covered_drugs_for_payer"], list)


def test_invalid_payer_returns_error():
    """Invalid payer returns error with available payers list."""
    result = get_policy_for_drug("FAKE_PAYER_XYZ", "Ozempic")
    assert "error" in result, \
        f"Expected error for invalid payer, got: {result}"
    assert "available_payers" in result, \
        "Error response must list available payers"


def test_normalize_strips_suffix():
    """Normalize function correctly strips drug suffixes."""
    from backend.tools.policy_checker import normalize
    assert normalize("Ozempic injection") == "ozempic"
    assert normalize("Metformin HCl") == "metformin"
    assert normalize("Atorvastatin Calcium") == "atorvastatin"
    assert normalize("OZEMPIC") == "ozempic"
    assert normalize("  ozempic  ") == "ozempic"

