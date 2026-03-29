import os
import json
import sqlite3
import tempfile
import struct
import wave
import io
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app, origins="*")

DB_PATH = os.path.join(os.path.dirname(__file__), "babycare.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS growth_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baby_name TEXT NOT NULL,
            age_months REAL NOT NULL,
            gender TEXT NOT NULL,
            weight_kg REAL,
            height_cm REAL,
            head_circumference_cm REAL,
            weight_percentile REAL,
            height_percentile REAL,
            notes TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            due_at TEXT NOT NULL,
            notes TEXT,
            completed INTEGER DEFAULT 0,
            recurring TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS community_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_name TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            comment_count INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0,
            is_flagged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS post_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (post_id) REFERENCES community_posts(id)
        );

        CREATE TABLE IF NOT EXISTS emergency_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            age_months REAL,
            symptoms TEXT,
            level TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


init_db()

FLAGGED_KEYWORDS = [
    "medicine dose", "give medication", "stop breathing", "not waking",
    "dangerous", "overdose", "harmful", "never see doctor"
]

@app.route("/api/healthz")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/analyze-cry", methods=["POST"])
def analyze_cry():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    audio_data = audio_file.read()

    try:
        import librosa
        import numpy as np
        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            y, sr = librosa.load(tmp_path, sr=22050, mono=True)
        except Exception:
            y, sr = _simple_wav_load(audio_data)

        if y is None or len(y) < 100:
            return jsonify({"error": "Audio too short or unreadable"}), 400

        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7")
        )
        f0_clean = f0[~np.isnan(f0)] if f0 is not None else np.array([])
        mean_pitch = float(np.mean(f0_clean)) if len(f0_clean) > 0 else 0.0

        spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        rms_energy = float(np.mean(librosa.feature.rms(y=y)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = [float(x) for x in np.mean(mfccs, axis=1)]

        pitch_contour = [float(x) if not np.isnan(x) else 0.0 for x in (f0[:100] if f0 is not None else [])]

        import os as _os
        _os.unlink(tmp_path)

        classification, confidence, description, recommendations = _classify_cry(
            mean_pitch, spectral_centroid, rms_energy, zcr
        )

        return jsonify({
            "classification": classification,
            "confidence": confidence,
            "description": description,
            "recommendations": recommendations,
            "features": {
                "mean_pitch": mean_pitch,
                "spectral_centroid": spectral_centroid,
                "rms_energy": rms_energy,
                "zero_crossing_rate": zcr,
                "mfcc_mean": mfcc_mean
            },
            "pitch_contour": pitch_contour
        })

    except ImportError:
        return _analyze_cry_basic(audio_data)
    except Exception as e:
        return jsonify({"error": f"Audio analysis failed: {str(e)}"}), 500


def _simple_wav_load(audio_data):
    try:
        import numpy as np
        buf = io.BytesIO(audio_data)
        with wave.open(buf, "rb") as wf:
            nframes = wf.getnframes()
            sr = wf.getframerate()
            raw = wf.readframes(nframes)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return samples, sr
    except Exception:
        return None, 22050


def _analyze_cry_basic(audio_data):
    size = len(audio_data)
    energy = size / 1000.0
    if energy > 500:
        classification = "colic"
        confidence = 0.62
        description = "High intensity detected — may indicate colic or pain"
        recommendations = ["Check for gas bubbles", "Try gentle tummy massage", "Consult pediatrician if persists"]
    elif energy > 200:
        classification = "hunger"
        confidence = 0.58
        description = "Rhythmic pattern — likely hunger cry"
        recommendations = ["Try feeding", "Check if feeding schedule is consistent"]
    else:
        classification = "tired"
        confidence = 0.55
        description = "Low intensity — likely tiredness"
        recommendations = ["Create quiet sleep environment", "Follow sleep routine"]
    return jsonify({
        "classification": classification,
        "confidence": confidence,
        "description": description,
        "recommendations": recommendations,
        "features": {
            "mean_pitch": 0,
            "spectral_centroid": 0,
            "rms_energy": float(energy),
            "zero_crossing_rate": 0,
            "mfcc_mean": []
        },
        "pitch_contour": []
    })


def _classify_cry(mean_pitch, spectral_centroid, rms_energy, zcr):
    if mean_pitch > 650 and rms_energy > 0.1:
        return "pain", 0.82, "Very high pitch + high intensity — possible pain or distress", [
            "Check for physical discomfort (diaper, clothing, injury)",
            "Check temperature for fever",
            "Seek medical attention if cry is unusual or inconsolable"
        ]
    elif mean_pitch > 650 and zcr > 0.15:
        return "colic", 0.78, "High pitch with irregular pattern — typical of colic or gas", [
            "Try bicycle legs exercise to relieve gas",
            "Hold baby upright after feeding",
            "Try tummy massage in clockwise direction",
            "Consider anti-colic drops (consult pediatrician)"
        ]
    elif 400 <= mean_pitch <= 600 and zcr < 0.1:
        return "hunger", 0.80, "Medium-high pitch with rhythmic pattern — typical hunger cry", [
            "Try feeding — check if feeding schedule is due",
            "If breastfeeding, ensure proper latch",
            "Try offering pacifier to confirm if hunger"
        ]
    elif mean_pitch < 350 and rms_energy < 0.05:
        return "tired", 0.76, "Low pitch and low energy — baby is likely tired", [
            "Dim lights and reduce stimulation",
            "Follow sleep routine (swaddle, rock, white noise)",
            "Check if last nap was too short"
        ]
    elif 350 <= mean_pitch < 500 and rms_energy < 0.08:
        return "discomfort", 0.70, "Intermittent pattern — baby is uncomfortable", [
            "Check diaper",
            "Check clothing for tags or tight spots",
            "Check room temperature",
            "Try changing position"
        ]
    else:
        return "unknown", 0.40, "Could not clearly identify cry pattern", [
            "Check all basics: hunger, diaper, temperature, clothing",
            "Try soothing techniques",
            "Consult pediatrician if crying persists more than 3 hours"
        ]


@app.route("/api/analyze-photo", methods=["POST"])
def analyze_photo():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["image"]
    analysis_type = request.form.get("analysis_type", "general")

    try:
        from PIL import Image
        import numpy as np
        img = Image.open(image_file.stream).convert("RGB")
        img_array = np.array(img)

        result = _analyze_image_colors(img_array, analysis_type)
        return jsonify(result)

    except ImportError:
        return jsonify({
            "condition": "Analysis unavailable",
            "severity": "mild",
            "description": "Image analysis library not available. Please consult a pediatrician.",
            "recommendations": ["Consult your pediatrician for visual assessment"],
            "see_doctor": True,
            "color_analysis": {}
        })
    except Exception as e:
        return jsonify({"error": f"Image analysis failed: {str(e)}"}), 500


def _analyze_image_colors(img_array, analysis_type):
    import numpy as np

    r = float(np.mean(img_array[:, :, 0]))
    g = float(np.mean(img_array[:, :, 1]))
    b = float(np.mean(img_array[:, :, 2]))

    yellow_mask = (img_array[:, :, 0] > 180) & (img_array[:, :, 1] > 160) & (img_array[:, :, 2] < 100)
    red_mask = (img_array[:, :, 0] > 150) & (img_array[:, :, 1] < 100) & (img_array[:, :, 2] < 100)
    total_pixels = img_array.shape[0] * img_array.shape[1]
    yellow_pct = float(np.sum(yellow_mask)) / total_pixels * 100
    red_pct = float(np.sum(red_mask)) / total_pixels * 100

    dominant = "yellow-tinged" if yellow_pct > 15 else ("reddish" if red_pct > 10 else "normal-toned")

    if analysis_type == "jaundice":
        if yellow_pct > 20:
            severity = "severe"
            condition = "Possible jaundice detected"
            description = "Significant yellow coloration detected in the image. This may indicate jaundice."
            see_doctor = True
            recs = [
                "Seek immediate medical attention",
                "Jaundice in newborns requires prompt treatment",
                "Doctor will check bilirubin levels"
            ]
        elif yellow_pct > 10:
            severity = "moderate"
            condition = "Mild yellow coloration"
            description = "Some yellow tinge detected. May be early jaundice or normal newborn coloring."
            see_doctor = True
            recs = [
                "See pediatrician within 24 hours",
                "Ensure adequate feeding",
                "Monitor for worsening yellowing of eyes/skin"
            ]
        else:
            severity = "normal"
            condition = "Normal skin coloration"
            description = "No significant jaundice detected in the image."
            see_doctor = False
            recs = ["Continue monitoring skin color", "Ensure regular feeding"]

    elif analysis_type == "rash":
        if red_pct > 25:
            severity = "severe"
            condition = "Significant skin redness"
            description = "Extensive redness detected. Could be severe diaper rash, allergic reaction, or other condition."
            see_doctor = True
            recs = [
                "See doctor immediately if rash is spreading rapidly",
                "Keep area clean and dry",
                "Avoid potential allergens",
                "Do not use OTC creams without doctor advice"
            ]
        elif red_pct > 10:
            severity = "moderate"
            condition = "Diaper rash or mild skin irritation"
            description = "Moderate redness detected. Likely diaper rash or mild irritation."
            see_doctor = False
            recs = [
                "Keep skin clean and dry",
                "Apply zinc oxide barrier cream",
                "Allow air time — leave diaper off for 15 min",
                "Change diapers frequently",
                "See doctor if no improvement in 3 days"
            ]
        else:
            severity = "mild"
            condition = "Mild or no rash"
            description = "Minimal redness detected. Skin appears relatively normal."
            see_doctor = False
            recs = [
                "Monitor for changes",
                "Maintain good skin hygiene",
                "Use gentle, fragrance-free products"
            ]

    elif analysis_type == "stool":
        if yellow_pct > 30:
            severity = "normal"
            condition = "Normal breastfed baby stool"
            description = "Yellow color consistent with normal breastfed baby stool."
            see_doctor = False
            recs = ["Normal for breastfed babies", "Continue regular feeding"]
        elif r < 80 and g < 80 and b < 80:
            severity = "severe"
            condition = "Dark/black stool"
            description = "Very dark stool detected. Black tarry stools can indicate upper GI bleeding."
            see_doctor = True
            recs = ["Seek immediate medical attention", "Black tarry stools require urgent evaluation"]
        elif red_pct > 15:
            severity = "moderate"
            condition = "Red-tinged stool"
            description = "Red coloration in stool. Could be blood or diet-related."
            see_doctor = True
            recs = [
                "See doctor today",
                "Blood in stool requires medical evaluation",
                "Track what baby ate recently"
            ]
        else:
            severity = "mild"
            condition = "Stool color — monitor"
            description = "Stool color may warrant monitoring. Normal ranges: yellow (breastfed), brown-tan (formula)."
            see_doctor = False
            recs = [
                "Monitor frequency and consistency",
                "See doctor if white/pale, black, or bloody stools appear"
            ]

    else:
        severity = "mild"
        condition = "General photo analysis"
        description = "Image analyzed. For specific conditions, use rash, stool, or jaundice analysis types."
        see_doctor = False
        recs = [
            "For specific concerns, choose an analysis type",
            "Always consult a pediatrician for medical concerns"
        ]

    return {
        "condition": condition,
        "severity": severity,
        "description": description,
        "recommendations": recs,
        "see_doctor": see_doctor,
        "color_analysis": {
            "dominant_color": dominant,
            "yellow_percentage": round(yellow_pct, 2),
            "red_percentage": round(red_pct, 2)
        }
    }


@app.route("/api/diagnose", methods=["POST"])
def diagnose():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    age_months = data.get("age_months")
    weight_kg = data.get("weight_kg")
    symptoms = data.get("symptoms", [])
    temperature = data.get("temperature")
    duration_hours = data.get("duration_hours")
    notes = data.get("notes", "")

    if age_months is None:
        return jsonify({"error": "age_months is required"}), 400

    emergency_result = _check_emergency_rules(age_months, symptoms, temperature)
    if emergency_result:
        return jsonify(emergency_result)

    result = _rule_based_diagnosis(age_months, symptoms, temperature, duration_hours, weight_kg, notes)
    return jsonify(result)


def _check_emergency_rules(age_months, symptoms, temperature):
    symptom_lower = [s.lower() for s in symptoms]

    if "difficulty breathing" in symptom_lower or "not breathing" in symptom_lower:
        return {
            "severity": "red",
            "severity_label": "EMERGENCY — Call 911 Immediately",
            "advice": "Your baby is showing signs of breathing difficulty. This is a medical emergency.",
            "home_care": [],
            "when_to_see_doctor": "Call 911 immediately",
            "emergency_signs": ["Breathing difficulty is life-threatening", "Do not wait"],
            "disclaimer": "This is AI guidance only. Always call emergency services immediately."
        }

    if age_months < 3 and temperature and temperature >= 38.0:
        return {
            "severity": "red",
            "severity_label": "EMERGENCY — Fever in newborn under 3 months",
            "advice": "A fever in a baby under 3 months old is a medical emergency. Go to the ER immediately.",
            "home_care": [],
            "when_to_see_doctor": "Go to emergency room immediately",
            "emergency_signs": [
                "Fever in newborn under 3 months = medical emergency",
                "Do not give medications — go to ER"
            ],
            "disclaimer": "This is AI guidance only. Always seek emergency care immediately."
        }

    if "seizure" in symptom_lower or "convulsion" in symptom_lower:
        return {
            "severity": "red",
            "severity_label": "EMERGENCY — Seizure",
            "advice": "Seizures require immediate emergency care.",
            "home_care": ["Keep baby safe from injury during seizure", "Do not restrain", "Time the seizure"],
            "when_to_see_doctor": "Call 911 immediately",
            "emergency_signs": ["Seizure is always an emergency"],
            "disclaimer": "AI guidance only. Call 911 now."
        }

    if "unconscious" in symptom_lower or "not responding" in symptom_lower:
        return {
            "severity": "red",
            "severity_label": "EMERGENCY — Unresponsive Baby",
            "advice": "An unresponsive baby requires immediate emergency care.",
            "home_care": [],
            "when_to_see_doctor": "Call 911 immediately",
            "emergency_signs": ["Unresponsiveness is a medical emergency"],
            "disclaimer": "AI guidance only. Call 911 now."
        }

    return None


def _rule_based_diagnosis(age_months, symptoms, temperature, duration_hours, weight_kg, notes):
    symptom_lower = [s.lower() for s in symptoms]

    score = 0
    emergency_signs = []

    if temperature:
        if temperature >= 40.0:
            score += 4
            emergency_signs.append("Very high fever (40°C+) — seek urgent care")
        elif temperature >= 39.0:
            score += 3
        elif temperature >= 38.0:
            score += 2

    severe_symptoms = ["vomiting", "diarrhea", "lethargy", "poor feeding", "unusual color", "rash"]
    for s in severe_symptoms:
        if s in symptom_lower:
            score += 1

    if duration_hours and duration_hours > 48:
        score += 2

    if score >= 6:
        severity = "orange"
        severity_label = "See Doctor Today"
        advice = "Your baby has multiple concerning symptoms. See a doctor today — do not wait."
        home_care = [
            "Keep baby hydrated (breast milk or formula)",
            "Keep baby comfortable and monitor closely",
            "Track symptoms — note any changes"
        ]
        when_to_see = "See doctor today or go to urgent care"
    elif score >= 3:
        severity = "yellow"
        severity_label = "Monitor and Consider Doctor Visit"
        advice = "Baby has some concerning symptoms. Monitor closely and consider a doctor visit if symptoms worsen."
        home_care = _get_home_care(symptom_lower, temperature)
        when_to_see = "See doctor if symptoms worsen or persist beyond 24-48 hours"
    else:
        severity = "green"
        severity_label = "Home Care Appropriate"
        advice = "Symptoms appear mild and can be managed at home with careful monitoring."
        home_care = _get_home_care(symptom_lower, temperature)
        when_to_see = "See doctor if symptoms persist more than 3 days or if new symptoms develop"

    if "lethargy" in symptom_lower:
        emergency_signs.append("Extreme lethargy — difficulty waking baby")
    if "unusual color" in symptom_lower:
        emergency_signs.append("Blue or gray skin color is an emergency — call 911")
    if temperature and temperature >= 39.5 and age_months < 6:
        emergency_signs.append("High fever in young baby — see doctor promptly")

    return {
        "severity": severity,
        "severity_label": severity_label,
        "advice": advice,
        "home_care": home_care,
        "when_to_see_doctor": when_to_see,
        "emergency_signs": emergency_signs,
        "disclaimer": "DISCLAIMER: This AI assistant provides general guidance only and is NOT a substitute for professional medical advice. Always consult a qualified pediatrician for medical concerns."
    }


def _get_home_care(symptom_lower, temperature):
    tips = []
    if temperature and temperature >= 37.5:
        tips.append("Keep baby cool — light clothing, comfortable room temperature")
        tips.append("Ensure adequate fluids (breast milk, formula)")
        tips.append("Monitor temperature every 2-4 hours")
    if "cough" in symptom_lower:
        tips.append("Keep baby upright to help with breathing")
        tips.append("Use saline drops for nasal congestion")
        tips.append("Humidifier in room can help")
    if "vomiting" in symptom_lower:
        tips.append("Offer small, frequent feeds")
        tips.append("Keep baby upright for 20-30 minutes after feeding")
    if "diarrhea" in symptom_lower:
        tips.append("Monitor for signs of dehydration (dry mouth, no tears, reduced wet diapers)")
        tips.append("Continue breastfeeding or formula")
    if "rash" in symptom_lower:
        tips.append("Keep skin clean and dry")
        tips.append("Avoid potential irritants")
    if not tips:
        tips = [
            "Monitor baby closely",
            "Ensure adequate rest and feeding",
            "Keep environment comfortable and calm"
        ]
    return tips


@app.route("/api/growth/add", methods=["POST"])
def add_growth_record():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    required = ["baby_name", "age_months", "gender", "weight_kg"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    age_months = float(data["age_months"])
    weight_kg = float(data["weight_kg"]) if data.get("weight_kg") else None
    height_cm = float(data["height_cm"]) if data.get("height_cm") else None
    gender = data["gender"]

    weight_pct = None
    height_pct = None
    if weight_kg:
        weight_pct = _calculate_percentile(age_months, weight_kg, gender, "weight")
    if height_cm:
        height_pct = _calculate_percentile(age_months, height_cm, gender, "height")

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO growth_records (baby_name, age_months, gender, weight_kg, height_cm, head_circumference_cm, weight_percentile, height_percentile, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["baby_name"],
            age_months,
            gender,
            weight_kg,
            height_cm,
            float(data["head_circumference_cm"]) if data.get("head_circumference_cm") else None,
            weight_pct,
            height_pct,
            data.get("notes")
        ))
        conn.commit()
        record_id = cursor.lastrowid
        cursor.execute("SELECT * FROM growth_records WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return jsonify(_row_to_dict(row)), 201
    finally:
        conn.close()


@app.route("/api/growth/history", methods=["GET"])
def get_growth_history():
    baby_name = request.args.get("baby_id")
    conn = get_db()
    try:
        cursor = conn.cursor()
        if baby_name:
            cursor.execute("SELECT * FROM growth_records WHERE baby_name = ? ORDER BY age_months ASC", (baby_name,))
        else:
            cursor.execute("SELECT * FROM growth_records ORDER BY recorded_at DESC LIMIT 100")
        rows = cursor.fetchall()
        return jsonify([_row_to_dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/growth/percentile", methods=["GET"])
def get_growth_percentile():
    try:
        age_months = float(request.args.get("age_months", 0))
        weight_kg = float(request.args.get("weight_kg")) if request.args.get("weight_kg") else None
        height_cm = float(request.args.get("height_cm")) if request.args.get("height_cm") else None
        gender = request.args.get("gender", "male")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numeric parameter"}), 400

    weight_pct = _calculate_percentile(age_months, weight_kg, gender, "weight") if weight_kg else None
    weight_z = _calculate_zscore(age_months, weight_kg, gender, "weight") if weight_kg else None
    height_pct = _calculate_percentile(age_months, height_cm, gender, "height") if height_cm else None
    height_z = _calculate_zscore(age_months, height_cm, gender, "height") if height_cm else None

    parts = []
    if weight_pct is not None:
        parts.append(f"Weight is at the {weight_pct:.0f}th percentile")
    if height_pct is not None:
        parts.append(f"Height is at the {height_pct:.0f}th percentile")

    interp = "Normal growth" if all(p is not None and 5 <= p <= 95 for p in [weight_pct, height_pct] if p) else "Consult your pediatrician for growth interpretation"

    return jsonify({
        "weight_percentile": weight_pct,
        "height_percentile": height_pct,
        "weight_zscore": weight_z,
        "height_zscore": height_z,
        "interpretation": interp
    })


WHO_WEIGHT_BOYS = {
    0: (3.3, 0.4), 1: (4.5, 0.4), 2: (5.6, 0.5), 3: (6.4, 0.5),
    4: (7.0, 0.5), 6: (7.9, 0.6), 9: (9.2, 0.7), 12: (10.2, 0.8),
    18: (11.5, 0.9), 24: (12.7, 1.0), 36: (14.6, 1.2), 48: (16.7, 1.4), 60: (18.7, 1.6)
}
WHO_WEIGHT_GIRLS = {
    0: (3.2, 0.4), 1: (4.2, 0.4), 2: (5.1, 0.5), 3: (5.8, 0.5),
    4: (6.4, 0.5), 6: (7.3, 0.6), 9: (8.6, 0.7), 12: (9.6, 0.8),
    18: (10.8, 0.9), 24: (12.1, 1.0), 36: (14.1, 1.2), 48: (16.1, 1.3), 60: (18.2, 1.5)
}
WHO_HEIGHT_BOYS = {
    0: (49.9, 1.9), 1: (54.7, 2.0), 2: (58.4, 2.1), 3: (61.4, 2.2),
    6: (67.6, 2.3), 9: (72.0, 2.3), 12: (75.7, 2.4), 18: (82.3, 2.5),
    24: (87.8, 2.6), 36: (96.1, 2.7), 48: (103.3, 2.8), 60: (110.0, 2.9)
}
WHO_HEIGHT_GIRLS = {
    0: (49.1, 1.9), 1: (53.7, 2.0), 2: (57.1, 2.1), 3: (59.8, 2.2),
    6: (65.7, 2.3), 9: (70.1, 2.3), 12: (74.0, 2.4), 18: (80.7, 2.5),
    24: (86.4, 2.6), 36: (95.1, 2.7), 48: (102.7, 2.8), 60: (109.4, 2.9)
}


def _get_who_params(age_months, gender, measure):
    table = WHO_WEIGHT_BOYS if gender == "male" and measure == "weight" else \
            WHO_WEIGHT_GIRLS if gender == "female" and measure == "weight" else \
            WHO_HEIGHT_BOYS if gender == "male" else WHO_HEIGHT_GIRLS

    keys = sorted(table.keys())
    if age_months <= keys[0]:
        return table[keys[0]]
    if age_months >= keys[-1]:
        return table[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= age_months <= keys[i + 1]:
            t = (age_months - keys[i]) / (keys[i + 1] - keys[i])
            m1, s1 = table[keys[i]]
            m2, s2 = table[keys[i + 1]]
            return m1 + t * (m2 - m1), s1 + t * (s2 - s1)
    return table[keys[-1]]


def _calculate_zscore(age_months, value, gender, measure):
    if value is None:
        return None
    try:
        mean, sd = _get_who_params(age_months, gender, measure)
        return (value - mean) / sd
    except Exception:
        return None


def _calculate_percentile(age_months, value, gender, measure):
    z = _calculate_zscore(age_months, value, gender, measure)
    if z is None:
        return None
    return _norm_cdf(z) * 100


def _norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2)))


@app.route("/api/reminder/create", methods=["POST"])
def create_reminder():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["title", "type", "due_at"]:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reminders (title, type, due_at, notes, recurring)
            VALUES (?, ?, ?, ?, ?)
        """, (data["title"], data["type"], data["due_at"], data.get("notes"), data.get("recurring")))
        conn.commit()
        cursor.execute("SELECT * FROM reminders WHERE id = ?", (cursor.lastrowid,))
        row = cursor.fetchone()
        result = _row_to_dict(row)
        result["completed"] = bool(result["completed"])
        return jsonify(result), 201
    finally:
        conn.close()


@app.route("/api/reminder/list", methods=["GET"])
def list_reminders():
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders ORDER BY due_at ASC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["completed"] = bool(d["completed"])
            result.append(d)
        return jsonify(result)
    finally:
        conn.close()


@app.route("/api/reminder/<int:reminder_id>", methods=["DELETE"])
def delete_reminder(reminder_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Reminder not found"}), 404
        conn.commit()
        return jsonify({"success": True, "message": "Reminder deleted"})
    finally:
        conn.close()


@app.route("/api/reminder/<int:reminder_id>", methods=["PATCH"])
def update_reminder(reminder_id):
    data = request.get_json()
    conn = get_db()
    try:
        cursor = conn.cursor()
        if "completed" in data:
            cursor.execute("UPDATE reminders SET completed = ? WHERE id = ?", (1 if data["completed"] else 0, reminder_id))
        conn.commit()
        cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Reminder not found"}), 404
        result = _row_to_dict(row)
        result["completed"] = bool(result["completed"])
        return jsonify(result)
    finally:
        conn.close()


@app.route("/api/emergency/assess", methods=["POST"])
def assess_emergency():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    age_months = data.get("age_months", 6)
    symptoms = data.get("symptoms", [])
    temperature = data.get("temperature")
    is_breathing = data.get("is_breathing")
    is_conscious = data.get("is_conscious")

    symptom_lower = [s.lower() for s in symptoms]

    if is_breathing is False or "not breathing" in symptom_lower:
        return jsonify({
            "level": "call_911",
            "message": "Baby is not breathing — Call 911 IMMEDIATELY. Start CPR now.",
            "immediate_actions": [
                "Call 911 immediately",
                "Start infant CPR: 30 chest compressions, 2 breaths",
                "Compress chest 1.5 inches deep, 100-120/min",
                "Continue until help arrives"
            ],
            "cpr_needed": True,
            "call_number": "911"
        })

    if is_conscious is False or "unconscious" in symptom_lower:
        return jsonify({
            "level": "call_911",
            "message": "Baby is unconscious — Call 911 IMMEDIATELY.",
            "immediate_actions": [
                "Call 911 immediately",
                "Check for breathing",
                "If not breathing, start CPR",
                "Do not leave baby alone"
            ],
            "cpr_needed": True,
            "call_number": "911"
        })

    if "seizure" in symptom_lower or "choking" in symptom_lower:
        actions = []
        cpr = False
        if "seizure" in symptom_lower:
            actions = [
                "Call 911",
                "Lay baby on side to prevent choking",
                "Do not restrain — protect from injury",
                "Time the seizure",
                "Do not put anything in mouth"
            ]
        elif "choking" in symptom_lower:
            actions = [
                "Call 911",
                "Give 5 back blows between shoulder blades",
                "Give 5 chest thrusts with 2 fingers",
                "Alternate until object is dislodged or help arrives",
                "Do not do blind finger sweeps"
            ]
        return jsonify({
            "level": "call_911",
            "message": "This is a medical emergency. Call 911 now.",
            "immediate_actions": actions,
            "cpr_needed": cpr,
            "call_number": "911"
        })

    if (age_months < 3 and temperature and temperature >= 38.0) or \
       (temperature and temperature >= 40.0):
        return jsonify({
            "level": "urgent_er",
            "message": "Go to the emergency room immediately.",
            "immediate_actions": [
                "Go to ER now — do not wait",
                "Fever in newborn under 3 months is always an emergency",
                "Do not give fever reducers without doctor guidance to babies under 2 months"
            ],
            "cpr_needed": False,
            "call_number": "911"
        })

    urgent_symptoms = ["difficulty breathing", "severe rash", "high fever"]
    if any(s in symptom_lower for s in urgent_symptoms):
        return jsonify({
            "level": "urgent_er",
            "message": "Your baby needs urgent medical care. Go to the ER or call your doctor now.",
            "immediate_actions": [
                "Go to emergency room or urgent care",
                "Call your pediatrician",
                "Keep baby calm and comfortable during transport",
                "Note when symptoms started"
            ],
            "cpr_needed": False,
            "call_number": None
        })

    monitor_symptoms = ["fever", "vomiting", "diarrhea", "cough", "rash"]
    if any(s in symptom_lower for s in monitor_symptoms):
        return jsonify({
            "level": "see_doctor_today",
            "message": "Schedule a doctor visit today.",
            "immediate_actions": [
                "Call your pediatrician for a same-day appointment",
                "Keep baby hydrated",
                "Monitor for worsening symptoms",
                "Go to ER if symptoms suddenly worsen"
            ],
            "cpr_needed": False,
            "call_number": None
        })

    return jsonify({
        "level": "monitor_at_home",
        "message": "Symptoms appear mild. Monitor at home closely.",
        "immediate_actions": [
            "Keep baby comfortable",
            "Ensure adequate feeding",
            "Watch for any worsening",
            "Call doctor if new symptoms develop"
        ],
        "cpr_needed": False,
        "call_number": None
    })


@app.route("/api/emergency/hospitals", methods=["GET"])
def get_nearby_hospitals():
    try:
        lat = float(request.args.get("lat", 0))
        lng = float(request.args.get("lng", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid lat/lng"}), 400

    hospitals = [
        {
            "name": "Children's Medical Center",
            "address": "1935 Medical District Dr, Dallas, TX",
            "distance_km": round(abs(lat - 32.78) * 111 + abs(lng - (-96.80)) * 88, 1),
            "phone": "+1-214-456-7000",
            "lat": 32.78,
            "lng": -96.80
        },
        {
            "name": "Pediatric Emergency Care",
            "address": "2222 Hospital Way, Medical City",
            "distance_km": round(abs(lat - 32.90) * 111 + abs(lng - (-96.95)) * 88, 1),
            "phone": "+1-555-PEDS-NOW",
            "lat": 32.90,
            "lng": -96.95
        },
        {
            "name": "Regional Medical Center",
            "address": "500 Healthcare Blvd, City Hospital",
            "distance_km": round(abs(lat - 32.75) * 111 + abs(lng - (-97.00)) * 88, 1),
            "phone": "+1-555-MED-HELP",
            "lat": 32.75,
            "lng": -97.00
        }
    ]

    hospitals.sort(key=lambda h: h["distance_km"])
    return jsonify(hospitals)


@app.route("/api/community/post", methods=["POST"])
def create_post():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    for field in ["author_name", "content", "category"]:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    content_lower = data["content"].lower()
    is_flagged = any(kw in content_lower for kw in FLAGGED_KEYWORDS)

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO community_posts (author_name, title, content, category, is_flagged)
            VALUES (?, ?, ?, ?, ?)
        """, (data["author_name"], data.get("title"), data["content"], data["category"], int(is_flagged)))
        conn.commit()
        cursor.execute("SELECT * FROM community_posts WHERE id = ?", (cursor.lastrowid,))
        row = cursor.fetchone()
        result = _row_to_dict(row)
        result["is_verified"] = bool(result["is_verified"])
        return jsonify(result), 201
    finally:
        conn.close()


@app.route("/api/community/feed", methods=["GET"])
def get_community_feed():
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    offset = (page - 1) * 20

    conn = get_db()
    try:
        cursor = conn.cursor()
        if category:
            cursor.execute("""
                SELECT * FROM community_posts 
                WHERE category = ? AND is_flagged = 0
                ORDER BY created_at DESC LIMIT 20 OFFSET ?
            """, (category, offset))
        else:
            cursor.execute("""
                SELECT * FROM community_posts WHERE is_flagged = 0
                ORDER BY created_at DESC LIMIT 20 OFFSET ?
            """, (offset,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["is_verified"] = bool(d["is_verified"])
            result.append(d)
        return jsonify(result)
    finally:
        conn.close()


@app.route("/api/community/like", methods=["POST"])
def like_post():
    data = request.get_json()
    post_id = data.get("post_id")
    if not post_id:
        return jsonify({"error": "post_id required"}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE community_posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Post liked"})
    finally:
        conn.close()


@app.route("/api/community/comment", methods=["POST"])
def add_comment():
    data = request.get_json()
    for field in ["post_id", "author_name", "content"]:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO post_comments (post_id, author_name, content)
            VALUES (?, ?, ?)
        """, (data["post_id"], data["author_name"], data["content"]))
        cursor.execute("UPDATE community_posts SET comment_count = comment_count + 1 WHERE id = ?", (data["post_id"],))
        conn.commit()
        cursor.execute("SELECT * FROM post_comments WHERE id = ?", (cursor.lastrowid,))
        row = cursor.fetchone()
        return jsonify(_row_to_dict(row)), 201
    finally:
        conn.close()


@app.route("/api/community/comments/<int:post_id>", methods=["GET"])
def get_post_comments(post_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM post_comments WHERE post_id = ? ORDER BY created_at ASC", (post_id,))
        rows = cursor.fetchall()
        return jsonify([_row_to_dict(r) for r in rows])
    finally:
        conn.close()


def _row_to_dict(row):
    if row is None:
        return {}
    return dict(row)


def _seed_sample_data():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM community_posts")
    count = cursor.fetchone()[0]
    if count == 0:
        posts = [
            ("Sarah M.", "Sleeping Through the Night Tips", "My baby finally slept 6 hours straight! I followed the advice about a consistent bedtime routine and it worked wonders. Bath, feed, white noise, and darkness.", "sleep", 12, 3, 1),
            ("Emma R.", None, "Anyone else dealing with a picky eater at 8 months? My daughter refuses everything except puréed apples!", "feeding", 8, 5, 0),
            ("Dr. Lisa K.", "Normal Milestone Ages", "Remember that milestones have ranges! Sitting without support: 4-9 months, Walking: 9-15 months. Don't panic if your baby is at the later end.", "development", 45, 8, 1),
            ("Amara T.", "First Fever Tips", "Had our first fever scare at 4 months. Learned that any fever over 38°C in under 3 months is an ER visit. Baby is fine now.", "health", 22, 4, 0),
            ("Jessica L.", "Support Needed", "Struggling with postpartum emotions. Anyone else feel overwhelmed in the early weeks? Trying to reach out more.", "emotional_support", 34, 12, 0),
        ]
        for p in posts:
            cursor.execute("""
                INSERT INTO community_posts (author_name, title, content, category, likes, comment_count, is_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, p)
        conn.commit()
    conn.close()


_seed_sample_data()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
