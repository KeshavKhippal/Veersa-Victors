"""
MedAuth Sentinel — Synthetic Data Generator
Generates all 5 JSON data files into the /data/ folder.
Usage: python backend/generate_data.py
"""

import json
import os
import sys
import random
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def random_date(start_year, end_year):
    """Generate a random date string between start_year and end_year."""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")


def random_phone():
    """Generate a realistic 10-digit Indian phone number starting with 9."""
    return "9" + "".join([str(random.randint(0, 9)) for _ in range(9)])


def generate_patients():
    """Generate 20 patients with realistic Indian names."""
    male_names = [
        "Arjun Sharma", "Vikram Patel", "Rajesh Kumar", "Amit Verma",
        "Suresh Gupta", "Deepak Mehta", "Rahul Joshi", "Sanjay Reddy",
        "Manish Agarwal", "Kiran Nair"
    ]
    female_names = [
        "Priya Singh", "Anita Desai", "Sunita Rao", "Meera Iyer",
        "Kavita Malhotra", "Neha Chatterjee", "Pooja Bhat", "Divya Menon",
        "Rekha Saxena", "Swati Kulkarni"
    ]
    cities = [
        "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad",
        "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"
    ]
    payers = ["BlueCross", "Aetna", "UnitedHealth", "Cigna"]

    patients = []
    all_names = male_names + female_names
    random.shuffle(all_names)

    for i in range(20):
        pid = f"P{str(i + 1).zfill(3)}"
        name = all_names[i]
        gender = "M" if name in male_names else "F"
        patients.append({
            "patient_id": pid,
            "name": name,
            "age": random.randint(30, 75),
            "gender": gender,
            "insurance_id": f"INS-{random.randint(1000, 9999)}",
            "payer": payers[i % len(payers)],
            "phone": random_phone(),
            "city": random.choice(cities)
        })

    patients[0]["payer"] = "BlueCross"
    patients[4]["payer"] = "BlueCross"
    patients[9]["payer"] = "Aetna"

    return patients


def generate_diagnoses(patients):
    """Generate diagnoses for all 20 patients with real ICD-10 codes."""
    diagnosis_pool = [
        ("I10", "Essential Hypertension"),
        ("E78.5", "Hyperlipidemia, unspecified"),
        ("J45.909", "Unspecified asthma, uncomplicated"),
        ("M54.5", "Low back pain"),
    ]

    diagnoses = []

    for p in patients:
        pid = p["patient_id"]

        if pid == "P001":
            diagnoses.append({
                "patient_id": pid,
                "icd10_code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "diagnosed_date": random_date(2020, 2023)
            })
        elif pid == "P005":
            diagnoses.append({
                "patient_id": pid,
                "icd10_code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "diagnosed_date": random_date(2020, 2023)
            })
        elif pid == "P010":
            diagnoses.append({
                "patient_id": pid,
                "icd10_code": "E11.65",
                "description": "Type 2 diabetes mellitus with hyperglycemia",
                "diagnosed_date": random_date(2020, 2023)
            })
        else:
            code, desc = random.choice(diagnosis_pool)
            diagnoses.append({
                "patient_id": pid,
                "icd10_code": code,
                "description": desc,
                "diagnosed_date": random_date(2020, 2024)
            })

        if random.random() < 0.3 and pid not in ("P001", "P005", "P010"):
            code2, desc2 = random.choice(diagnosis_pool)
            diagnoses.append({
                "patient_id": pid,
                "icd10_code": code2,
                "description": desc2,
                "diagnosed_date": random_date(2021, 2024)
            })

    return diagnoses


def generate_medications(patients):
    """Generate current medications for all 20 patients."""
    med_pool = [
        ("Lisinopril", "10mg"),
        ("Atorvastatin", "40mg"),
        ("Amlodipine", "5mg"),
        ("Omeprazole", "20mg"),
        ("Albuterol", "90mcg"),
        ("Losartan", "50mg"),
        ("Hydrochlorothiazide", "25mg"),
        ("Gabapentin", "300mg"),
    ]

    medications = []

    for p in patients:
        pid = p["patient_id"]

        if pid == "P001":
            medications.append({
                "patient_id": pid,
                "drug_name": "Metformin",
                "dosage": "500mg",
                "started_date": random_date(2020, 2023),
                "status": "active"
            })
            medications.append({
                "patient_id": pid,
                "drug_name": "Lisinopril",
                "dosage": "10mg",
                "started_date": random_date(2021, 2023),
                "status": "active"
            })
        elif pid == "P005":
            medications.append({
                "patient_id": pid,
                "drug_name": "Atorvastatin",
                "dosage": "20mg",
                "started_date": random_date(2021, 2024),
                "status": "active"
            })
            medications.append({
                "patient_id": pid,
                "drug_name": "Amlodipine",
                "dosage": "5mg",
                "started_date": random_date(2022, 2024),
                "status": "active"
            })
        elif pid == "P010":
            medications.append({
                "patient_id": pid,
                "drug_name": "Metformin",
                "dosage": "1000mg",
                "started_date": random_date(2020, 2022),
                "status": "active"
            })
            medications.append({
                "patient_id": pid,
                "drug_name": "Glimepiride",
                "dosage": "2mg",
                "started_date": random_date(2022, 2024),
                "status": "active"
            })
        else:
            num_meds = random.randint(1, 2)
            chosen = random.sample(med_pool, num_meds)
            for drug, dose in chosen:
                medications.append({
                    "patient_id": pid,
                    "drug_name": drug,
                    "dosage": dose,
                    "started_date": random_date(2020, 2024),
                    "status": "active"
                })

    return medications


def generate_payer_policies():
    """Generate 8 payer policy rules."""
    policies = [
        {
            "policy_id": "POL-001",
            "payer": "BlueCross",
            "drug_name": "Ozempic",
            "requires_diagnosis": "E11.9",
            "requires_prior_drug_failure": "Metformin",
            "min_age": None,
            "max_age": None,
            "notes": "BlueCross requires Type 2 Diabetes (E11.9) diagnosis and prior Metformin trial before approving Ozempic."
        },
        {
            "policy_id": "POL-002",
            "payer": "Aetna",
            "drug_name": "Ozempic",
            "requires_diagnosis": "E11.9 OR E11.65",
            "requires_prior_drug_failure": "Metformin",
            "min_age": None,
            "max_age": None,
            "notes": "Aetna accepts both E11.9 and E11.65 (Type 2 Diabetes variants) for Ozempic. Requires prior Metformin trial."
        },
        {
            "policy_id": "POL-003",
            "payer": "UnitedHealth",
            "drug_name": "Humira",
            "requires_diagnosis": "M54.5",
            "requires_prior_drug_failure": None,
            "min_age": None,
            "max_age": None,
            "notes": "UnitedHealth requires Low Back Pain (M54.5) diagnosis for Humira. No prior drug requirement."
        },
        {
            "policy_id": "POL-004",
            "payer": "Cigna",
            "drug_name": "Advair",
            "requires_diagnosis": "J45.909",
            "requires_prior_drug_failure": None,
            "min_age": None,
            "max_age": None,
            "notes": "Cigna requires Asthma (J45.909) diagnosis for Advair. No prior drug requirement."
        },
        {
            "policy_id": "POL-005",
            "payer": "BlueCross",
            "drug_name": "Jardiance",
            "requires_diagnosis": "E11.9",
            "requires_prior_drug_failure": "Metformin",
            "min_age": None,
            "max_age": None,
            "notes": "BlueCross requires Type 2 Diabetes (E11.9) diagnosis and prior Metformin trial for Jardiance."
        },
        {
            "policy_id": "POL-006",
            "payer": "Aetna",
            "drug_name": "Lipitor",
            "requires_diagnosis": "E78.5",
            "requires_prior_drug_failure": None,
            "min_age": None,
            "max_age": None,
            "notes": "Aetna requires Hyperlipidemia (E78.5) diagnosis for Lipitor. No prior drug requirement."
        },
        {
            "policy_id": "POL-007",
            "payer": "UnitedHealth",
            "drug_name": "Ozempic",
            "requires_diagnosis": "E11.9 OR E11.65",
            "requires_prior_drug_failure": "Metformin",
            "min_age": None,
            "max_age": None,
            "notes": "UnitedHealth accepts both E11.9 and E11.65 for Ozempic. Requires prior Metformin trial."
        },
        {
            "policy_id": "POL-008",
            "payer": "Cigna",
            "drug_name": "Ozempic",
            "requires_diagnosis": "E11.9",
            "requires_prior_drug_failure": None,
            "min_age": None,
            "max_age": None,
            "notes": "Cigna requires Type 2 Diabetes (E11.9) for Ozempic. No prior drug requirement."
        }
    ]
    return policies


def generate_prior_auths(patients):
    """Generate 10 past authorization records."""
    doctors = [
        "Dr. Mehta", "Dr. Singh", "Dr. Sharma", "Dr. Patel", "Dr. Reddy",
        "Dr. Gupta", "Dr. Iyer", "Dr. Desai", "Dr. Joshi", "Dr. Nair"
    ]

    prior_auths = [
        {
            "auth_id": "AUTH-001",
            "patient_id": "P001",
            "drug_requested": "Ozempic",
            "requesting_doctor": "Dr. Mehta",
            "payer": "BlueCross",
            "decision": "APPROVED",
            "reasoning": "Patient P001 has confirmed Type 2 Diabetes (E11.9) and has been on Metformin for over 12 months. All policy criteria met.",
            "date": "2024-01-15"
        },
        {
            "auth_id": "AUTH-002",
            "patient_id": "P005",
            "drug_requested": "Ozempic",
            "requesting_doctor": "Dr. Singh",
            "payer": "BlueCross",
            "decision": "DENIED",
            "reasoning": "Patient P005 has T2DM diagnosis but has not tried Metformin first as required by policy POL-001.",
            "date": "2024-02-20"
        },
        {
            "auth_id": "AUTH-003",
            "patient_id": "P003",
            "drug_requested": "Humira",
            "requesting_doctor": "Dr. Sharma",
            "payer": "UnitedHealth",
            "decision": "APPROVED",
            "reasoning": "Patient has confirmed Low Back Pain (M54.5). No prior drug requirement for this policy.",
            "date": "2023-11-10"
        },
        {
            "auth_id": "AUTH-004",
            "patient_id": "P004",
            "drug_requested": "Advair",
            "requesting_doctor": "Dr. Patel",
            "payer": "Cigna",
            "decision": "APPROVED",
            "reasoning": "Patient has confirmed Asthma (J45.909). Advair approved per policy POL-004.",
            "date": "2023-08-25"
        },
        {
            "auth_id": "AUTH-005",
            "patient_id": "P002",
            "drug_requested": "Jardiance",
            "requesting_doctor": "Dr. Reddy",
            "payer": "BlueCross",
            "decision": "DENIED",
            "reasoning": "Patient does not have a qualifying Type 2 Diabetes diagnosis for Jardiance.",
            "date": "2024-03-05"
        },
        {
            "auth_id": "AUTH-006",
            "patient_id": "P006",
            "drug_requested": "Lipitor",
            "requesting_doctor": "Dr. Gupta",
            "payer": "Aetna",
            "decision": "APPROVED",
            "reasoning": "Patient has Hyperlipidemia (E78.5). Lipitor approved per policy POL-006.",
            "date": "2023-06-18"
        },
        {
            "auth_id": "AUTH-007",
            "patient_id": "P010",
            "drug_requested": "Ozempic",
            "requesting_doctor": "Dr. Sharma",
            "payer": "Aetna",
            "decision": "PENDING",
            "reasoning": "Under review — patient has E11.65 variant. Checking if policy POL-002 covers this variant.",
            "date": "2024-04-01"
        },
        {
            "auth_id": "AUTH-008",
            "patient_id": "P008",
            "drug_requested": "Ozempic",
            "requesting_doctor": "Dr. Iyer",
            "payer": "UnitedHealth",
            "decision": "APPROVED",
            "reasoning": "Patient has E11.9 and prior Metformin use confirmed. All criteria met per POL-007.",
            "date": "2023-09-12"
        },
        {
            "auth_id": "AUTH-009",
            "patient_id": "P012",
            "drug_requested": "Advair",
            "requesting_doctor": "Dr. Desai",
            "payer": "Cigna",
            "decision": "DENIED",
            "reasoning": "Patient does not have Asthma diagnosis required for Advair.",
            "date": "2022-12-08"
        },
        {
            "auth_id": "AUTH-010",
            "patient_id": "P015",
            "drug_requested": "Humira",
            "requesting_doctor": "Dr. Nair",
            "payer": "UnitedHealth",
            "decision": "APPROVED",
            "reasoning": "Low back pain confirmed. Humira approved per standard policy.",
            "date": "2024-05-22"
        }
    ]

    return prior_auths


def save_json(data, filename):
    """Save data to a JSON file in the data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {filename}: {len(data)} records")


def main():
    print("=" * 50)
    print("MedAuth Sentinel — Data Generator")
    print("=" * 50)

    random.seed(42)

    print("\nGenerating data...\n")

    patients = generate_patients()
    save_json(patients, "patients.json")

    diagnoses = generate_diagnoses(patients)
    save_json(diagnoses, "diagnoses.json")

    medications = generate_medications(patients)
    save_json(medications, "medications.json")

    policies = generate_payer_policies()
    save_json(policies, "payer_policies.json")

    prior_auths = generate_prior_auths(patients)
    save_json(prior_auths, "prior_auths.json")

    print(f"\n✅ All 5 data files generated in: {DATA_DIR}")
    print("Run 'python verify_data.py' to validate the data.")


if __name__ == "__main__":
    main()
