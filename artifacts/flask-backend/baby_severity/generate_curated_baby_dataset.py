# This script is not random garbage.
#  It is a pattern-curated synthetic dataset shaped around pediatric escalation logic
#  such as fever in infants under 3 months, breathing problems, dehydration with vomiting/diarrhea, and high fever with lethargy. 
# Those are all consistent with the cited guidance.
import csv
import random

OUT_FILE = "curated_baby_severity_dataset.csv"
N_SAMPLES = 4000
SEED = 42

random.seed(SEED)

GENDERS = ["male", "female"]

def rand_weight(age_months: float) -> float:
    # Rough realistic infant/toddler growth range
    if age_months <= 1:
        base = random.uniform(3.0, 5.0)
    elif age_months <= 3:
        base = random.uniform(4.0, 7.0)
    elif age_months <= 6:
        base = random.uniform(5.5, 8.5)
    elif age_months <= 12:
        base = random.uniform(6.5, 10.5)
    elif age_months <= 24:
        base = random.uniform(8.5, 13.5)
    else:
        base = random.uniform(11.0, 18.0)
    return round(base, 1)

def maybe(p: float) -> int:
    return 1 if random.random() < p else 0

def choose_temperature(symptom_fever: int, age_months: float) -> float | None:
    if symptom_fever:
        # Fever distribution
        if age_months < 3 and random.random() < 0.35:
            return round(random.uniform(38.0, 39.2), 1)
        if random.random() < 0.2:
            return round(random.uniform(39.0, 40.3), 1)
        return round(random.uniform(37.8, 39.2), 1)
    else:
        if random.random() < 0.15:
            return round(random.uniform(36.7, 37.7), 1)
        return None

def make_case():
    age_months = round(random.uniform(0.0, 24.0), 1)
    gender = random.choice(GENDERS)
    weight_kg = rand_weight(age_months)
    duration_hours = round(random.uniform(1, 72), 1)

    # Base symptoms
    symptom_fever = maybe(0.40)
    symptom_cough = maybe(0.25)
    symptom_vomiting = maybe(0.18)
    symptom_diarrhea = maybe(0.16)
    symptom_rash = maybe(0.12)
    symptom_lethargy = maybe(0.10)
    symptom_poor_feeding = maybe(0.18)
    symptom_difficulty_breathing = maybe(0.06)
    symptom_dehydration = maybe(0.08)

    # Symptom co-occurrence shaping
    if symptom_vomiting:
        symptom_dehydration = max(symptom_dehydration, maybe(0.25))
    if symptom_diarrhea:
        symptom_dehydration = max(symptom_dehydration, maybe(0.20))
    if symptom_cough:
        symptom_difficulty_breathing = max(symptom_difficulty_breathing, maybe(0.10))
    if symptom_fever:
        symptom_lethargy = max(symptom_lethargy, maybe(0.15))
        symptom_poor_feeding = max(symptom_poor_feeding, maybe(0.18))

    temperature = choose_temperature(symptom_fever, age_months)

    # Severity curation based on real pediatric escalation logic
    severity = "green"
    pattern = "mild_non_specific"

    # Highest concern patterns
    if symptom_difficulty_breathing:
        severity = "orange"
        pattern = "breathing_concern"

    elif age_months < 3 and temperature is not None and temperature >= 38.0:
        severity = "orange"
        pattern = "young_infant_fever"

    elif temperature is not None and temperature >= 39.5 and (symptom_lethargy or symptom_poor_feeding):
        severity = "orange"
        pattern = "high_fever_lethargy"

    elif symptom_dehydration and (symptom_vomiting or symptom_diarrhea):
        severity = "orange" if duration_hours >= 24 else "yellow"
        pattern = "dehydration_gastro"

    elif symptom_lethargy and symptom_poor_feeding and symptom_fever:
        severity = "orange"
        pattern = "systemically_unwell"

    # Medium concern patterns
    elif temperature is not None and age_months < 6 and temperature >= 39.0:
        severity = "yellow"
        pattern = "young_baby_high_fever"

    elif symptom_vomiting and symptom_diarrhea:
        severity = "yellow"
        pattern = "gastroenteritis_moderate"

    elif symptom_fever and symptom_cough:
        severity = "yellow"
        pattern = "viral_fever_mild"

    elif symptom_rash and symptom_fever:
        severity = "yellow"
        pattern = "fever_with_rash"

    elif symptom_poor_feeding and duration_hours >= 12:
        severity = "yellow"
        pattern = "feeding_issue_monitor"

    elif symptom_lethargy:
        severity = "yellow"
        pattern = "lethargy_monitor"

    # Lower concern patterns
    elif symptom_rash:
        severity = "green"
        pattern = "mild_rash"

    elif symptom_cough:
        severity = "green"
        pattern = "mild_cough"

    elif symptom_fever:
        severity = "green"
        pattern = "low_grade_fever"

    if random.random() < 0.03:
        severity = random.choice(["green", "yellow", "orange"])

    return {
        "age_months": age_months,
        "weight_kg": weight_kg,
        "duration_hours": duration_hours,
        "temperature": temperature,
        "gender": gender,
        "symptom_fever": symptom_fever,
        "symptom_cough": symptom_cough,
        "symptom_vomiting": symptom_vomiting,
        "symptom_diarrhea": symptom_diarrhea,
        "symptom_rash": symptom_rash,
        "symptom_lethargy": symptom_lethargy,
        "symptom_poor_feeding": symptom_poor_feeding,
        "symptom_difficulty_breathing": symptom_difficulty_breathing,
        "symptom_dehydration": symptom_dehydration,
        "severity_label": severity,
        "clinical_pattern": pattern,
    }

def main():
    rows = [make_case() for _ in range(N_SAMPLES)]
    fieldnames = list(rows[0].keys())

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {OUT_FILE} with {len(rows)} rows")

if __name__ == "__main__":
    main()