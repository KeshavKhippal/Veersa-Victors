"""
MedAuth Sentinel — Policy Checker Tool
4-tier drug matching pipeline:
  Tier 1: Exact match (case-insensitive)
  Tier 2: Partial match (catches "Ozempic injection" → "Ozempic")
  Tier 3: Alias match (brand ↔ generic ↔ biosimilar)
  Tier 4: Agentic fallback (AI therapeutic equivalence reasoning)
"""

import json
from pathlib import Path

# ── PATH — works on both Windows and Linux ────────────────────────
ROOT_DIR = Path(__file__).parent.parent.parent
DATA_PATH = ROOT_DIR / "data" / "payer_policies.json"

# ── DRUG ALIAS MAP ────────────────────────────────────────────────
# Format: "normalized_name": ["alias1", "alias2", ...]
# Covers highest-volume PA drugs for deterministic speed.
# All keys and values must be lowercase with no extra spaces.
DRUG_ALIASES = {
    # GLP-1 receptor agonists (same active molecule: semaglutide)
    "ozempic":      ["semaglutide", "wegovy", "rybelsus",
                     "semaglutide injection", "semaglutide oral"],
    "wegovy":       ["semaglutide", "ozempic", "rybelsus"],
    "rybelsus":     ["semaglutide", "ozempic", "wegovy"],
    "semaglutide":  ["ozempic", "wegovy", "rybelsus"],

    # SGLT2 inhibitors
    "jardiance":     ["empagliflozin"],
    "empagliflozin": ["jardiance"],

    # Biguanides (diabetes)
    "metformin":     ["glucophage", "metformin hcl",
                      "metformin hydrochloride", "fortamet", "glumetza"],
    "glucophage":    ["metformin", "metformin hcl"],

    # Statins (cholesterol)
    "lipitor":        ["atorvastatin", "atorvastatin calcium"],
    "atorvastatin":   ["lipitor", "atorvastatin calcium"],
    "crestor":        ["rosuvastatin", "rosuvastatin calcium"],
    "rosuvastatin":   ["crestor", "rosuvastatin calcium"],
    "zocor":          ["simvastatin"],
    "simvastatin":    ["zocor"],

    # ACE inhibitors (blood pressure)
    "lisinopril":   ["zestril", "prinivil"],
    "zestril":      ["lisinopril", "prinivil"],
    "prinivil":     ["lisinopril", "zestril"],

    # ICS/LABA combinations (asthma)
    "advair":    ["fluticasone salmeterol", "fluticasone/salmeterol",
                  "wixela", "airduo"],
    "wixela":    ["advair", "fluticasone salmeterol"],
    "airduo":    ["advair", "fluticasone salmeterol"],

    # TNF inhibitors / biologics
    "humira":      ["adalimumab", "adalimumab-adaz", "hyrimoz",
                    "hadlima", "cyltezo", "yusimry"],
    "adalimumab":  ["humira", "hyrimoz", "hadlima", "cyltezo"],
    "hyrimoz":     ["adalimumab", "humira"],
    "hadlima":     ["adalimumab", "humira"],

    # Immunotherapy (checkpoint inhibitors)
    "keytruda":     ["pembrolizumab"],
    "pembrolizumab": ["keytruda"],
    "opdivo":       ["nivolumab"],
    "nivolumab":    ["opdivo"],
}


def normalize(name: str) -> str:
    """
    Lowercase, strip whitespace, remove common drug name suffixes.
    Examples:
      "Ozempic Injection" → "ozempic"
      "Metformin HCl"     → "metformin"
      "Atorvastatin Calcium 40mg" → "atorvastatin"
    """
    import re
    name = name.lower().strip()
    suffixes = [
        " injection", " oral", " tablet", " tablets",
        " capsule", " capsules", " solution", " suspension",
        " hcl", " hydrochloride", " calcium", " sodium",
        " acetate", " phosphate", " sulfate",
    ]
    # Remove dosage patterns like "40mg", "10 mg", "500 mg"
    name = re.sub(r'\s*\d+\s*mg\b', '', name)
    name = re.sub(r'\s*\d+\s*mcg\b', '', name)
    name = re.sub(r'\s*\d+\s*ml\b', '', name)

    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[: -len(suffix)]

    return name.strip()


def _load_policies() -> list:
    """Load payer_policies.json. Raises FileNotFoundError if missing."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"payer_policies.json not found at {DATA_PATH}. "
            "Run generate_data.py first."
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_policy_for_drug(payer: str, drug_name: str) -> dict:
    """
    Find the payer policy for a requested drug using 4-tier matching.

    Args:
        payer:     Payer name (e.g. "BlueCross", "Aetna")
        drug_name: Drug name as submitted (e.g. "Rybelsus", "semaglutide")

    Returns:
        dict — one of:
          - A policy dict with match_type added ("exact"/"partial"/"alias")
          - An agentic fallback dict with action_required="AGENT_MECHANISM_CHECK"
          - An error dict if payer not found at all
    """
    policies = _load_policies()

    payer_norm = payer.lower().strip()
    drug_norm  = normalize(drug_name)

    # Filter to this payer's policies only
    payer_policies = [
        p for p in policies
        if p.get("payer", "").lower().strip() == payer_norm
    ]

    if not payer_policies:
        return {
            "error": f"No policies found for payer '{payer}'.",
            "payer_searched": payer,
            "available_payers": list({
                p.get("payer") for p in policies
            })
        }

    # ── TIER 1: Exact match (case-insensitive + normalized) ───────
    for policy in payer_policies:
        policy_drug_norm = normalize(policy.get("drug_name", ""))
        if policy_drug_norm == drug_norm:
            result = dict(policy)
            result["match_type"] = "exact"
            return result

    # ── TIER 2: Partial match ─────────────────────────────────────
    # Catches "Ozempic injection" matching policy "Ozempic"
    for policy in payer_policies:
        policy_drug_norm = normalize(policy.get("drug_name", ""))
        if policy_drug_norm in drug_norm or drug_norm in policy_drug_norm:
            result = dict(policy)
            result["match_type"] = "partial"
            result["match_note"] = (
                f"'{drug_name}' matched policy drug "
                f"'{policy['drug_name']}' via partial match"
            )
            return result

    # ── TIER 3: Alias match ───────────────────────────────────────
    # Catches brand ↔ generic ↔ biosimilar equivalents
    aliases_to_check = DRUG_ALIASES.get(drug_norm, [])
    for alias in aliases_to_check:
        alias_norm = normalize(alias)
        for policy in payer_policies:
            policy_drug_norm = normalize(policy.get("drug_name", ""))
            if policy_drug_norm == alias_norm:
                result = dict(policy)
                result["match_type"] = "alias"
                result["match_note"] = (
                    f"'{drug_name}' matched policy drug "
                    f"'{policy['drug_name']}' via alias "
                    f"'{alias}' — therapeutically equivalent"
                )
                return result

    # ── TIER 4: Web Search + Agentic fallback ─────────────────────
    # All deterministic tiers failed.
    # Step 1: Search the web for this drug's pharmacological info
    # Step 2: Return web search results + payer context to agent
    print(f"[PolicyChecker] Tier 4 triggered for '{drug_name}' — initiating web search")

    from backend.tools.drug_search import (
        search_drug_info,
        format_search_result_for_agent
    )

    search_result = search_drug_info(drug_name)
    formatted_search = format_search_result_for_agent(search_result)

    print(f"[PolicyChecker] Web search complete — found: {search_result.get('found')}")

    covered_drug_names = [p.get("drug_name") for p in payer_policies]

    return {
        "status": "exact_match_failed",
        "match_type": "web_search",
        "requested_drug": drug_name,
        "drug_normalized": drug_norm,
        "payer": payer,
        "action_required": "AGENT_MECHANISM_CHECK",
        "web_search_conducted": True,
        "web_search_found": search_result.get("found", False),
        "web_search_summary": formatted_search,
        "active_ingredient_found": search_result.get("active_ingredient"),
        "mechanism_found": search_result.get("mechanism"),
        "drug_class_found": search_result.get("drug_class"),
        "instructions": (
            "Web search was conducted for this drug. "
            "Use the web_search_summary below as your primary source "
            "of pharmacological information. "
            "Cross-reference with covered_drugs_for_payer to determine "
            "if a therapeutically equivalent drug is covered."
        ),
        "covered_drugs_for_payer": covered_drug_names,
        "full_payer_policies": payer_policies,
        "aliases_checked": aliases_to_check,
    }


def get_all_policies() -> list:
    """Returns all policies. Used by tests and the API."""
    return _load_policies()
