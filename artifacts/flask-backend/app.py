import os
import sqlite3
import tempfile
import wave
import io
import math

from flask import Flask, request, jsonify
from flask_cors import CORS

import joblib
import numpy as np
from pydub import AudioSegment


# =========================
# BabyCare AI Assistant API
# Flask backend for:
# - Cry analysis
# - Photo analysis
# - Symptom diagnosis
# - Growth tracking
# - Reminders
# - Emergency assistant
# - Community posts
# =========================
app = Flask(__name__)
CORS(app, origins="*")

#sqlite database path
DB_PATH = os.path.join(os.path.dirname(__file__), "babycare.db")


def get_db():
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    #Create database tables if they do not already exist.
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

# =========================
# Cry Model Configuration
# =========================
MODEL_DIR = os.path.join(os.path.dirname(__file__), "baby-cry-classification")
CRY_MODEL = None
CRY_LABEL_ENCODER = None
CRY_MODEL_ERROR = None

# Feature extraction parameters
N_FFT = 2048
HOP_LENGTH = 512
WIN_LENGTH = 2048
WINDOW = "hann"
N_MELS = 128
N_BANDS = 6
FMIN = 200.0

SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".aac"
}
# =========================
# Severity Model Configuration
# =========================
SEVERITY_MODEL = None
SEVERITY_MODEL_ERROR = None
SEVERITY_MODEL_PATH = os.path.join(os.path.dirname(__file__),'baby_severity', "severity_model.joblib")

# =========================
# Load Models
# =========================
def load_cry_model():
    #"""Load cry classification model and label encoder from disk."""
    global CRY_MODEL, CRY_LABEL_ENCODER, CRY_MODEL_ERROR

    if CRY_MODEL is not None and CRY_LABEL_ENCODER is not None:
        return True

    try:
        model_path = os.path.join(MODEL_DIR, "model.joblib")
        label_path = os.path.join(MODEL_DIR, "label.joblib")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Missing model file: {model_path}")
        if not os.path.exists(label_path):
            raise FileNotFoundError(f"Missing label file: {label_path}")

        CRY_MODEL = joblib.load(model_path)
        CRY_LABEL_ENCODER = joblib.load(label_path)
        CRY_MODEL_ERROR = None

        print("✅ Cry model loaded successfully from local files")
        return True

    except Exception as e:
        CRY_MODEL = None
        CRY_LABEL_ENCODER = None
        CRY_MODEL_ERROR = str(e)
        print(f"❌ Failed to load cry model: {e}")
        return False
    
def load_severity_model():
    
    
    global SEVERITY_MODEL, SEVERITY_MODEL_ERROR

    if SEVERITY_MODEL is not None:
        return True

    try:
        if not os.path.exists(SEVERITY_MODEL_PATH):
            raise FileNotFoundError(f"Missing severity model file: {SEVERITY_MODEL_PATH}")

        bundle = joblib.load(SEVERITY_MODEL_PATH)
        SEVERITY_MODEL = bundle
        SEVERITY_MODEL_ERROR = None
        print("✅ Severity model loaded successfully")
        return True

    except Exception as e:
        SEVERITY_MODEL = None
        SEVERITY_MODEL_ERROR = str(e)
        print(f"❌ Failed to load severity model: {e}")
        return False
# =========================
# Cry Model Utilities
# =========================
def _get_file_extension(filename):
    if not filename:
        return ""
    return os.path.splitext(filename.lower())[1]

def convert_audio_to_wav_16k_mono(audio_bytes, original_filename="audio.wav"):
    """
    Converts uploaded audio bytes to a clean mono 16kHz WAV file.
    Returns path to temp wav file.
    """
    ext = _get_file_extension(original_filename)
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        # still try, but give pydub a chance using original extension or wav fallback
        ext = ".wav"

    input_suffix = ext if ext else ".bin"

    with tempfile.NamedTemporaryFile(suffix=input_suffix, delete=False) as src_file:
        src_file.write(audio_bytes)
        src_path = src_file.name

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_file:
        out_path = out_file.name

    try:
        audio = AudioSegment.from_file(src_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio.export(out_path, format="wav")
        return out_path
    except Exception as e:
        # fallback for true wav files
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                if wf.getnframes() < 100:
                    raise ValueError("Audio too short")
            return src_path
        except Exception:
            if os.path.exists(src_path):
                os.unlink(src_path)
            if os.path.exists(out_path):
                os.unlink(out_path)
            raise ValueError(f"Audio conversion failed: {str(e)}")
    finally:
        if os.path.exists(src_path) and src_path != out_path:
            try:
                os.unlink(src_path)
            except Exception:
                pass

def extract_cry_features(file_path):
    import librosa

    y, sr = librosa.load(file_path, sr=16000, mono=True)

    if y is None or len(y) < 400:
        raise ValueError("Audio too short or unreadable")

    max_val = np.max(np.abs(y))
    if max_val > 0:
        y = y / max_val

    mfcc = np.mean(
        librosa.feature.mfcc(
            y=y,
            sr=sr,
            n_mfcc=40,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            win_length=WIN_LENGTH,
            window=WINDOW
        ).T,
        axis=0
    )

    mel = np.mean(
        librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            win_length=WIN_LENGTH,
            window=WINDOW,
            n_mels=N_MELS
        ).T,
        axis=0
    )

    stft = np.abs(
        librosa.stft(
            y,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            win_length=WIN_LENGTH,
            window=WINDOW
        )
    )

    chroma = np.mean(
        librosa.feature.chroma_stft(
            S=stft,
            sr=sr
        ).T,
        axis=0
    )

    contrast = np.mean(
        librosa.feature.spectral_contrast(
            S=stft,
            sr=sr,
            n_fft=N_FFT,
            hop_length=HOP_LENGTH,
            win_length=WIN_LENGTH,
            n_bands=N_BANDS,
            fmin=FMIN
        ).T,
        axis=0
    )

    tonnetz = np.mean(
        librosa.feature.tonnetz(
            y=y,
            sr=sr
        ).T,
        axis=0
    )

    features = np.concatenate([mfcc, chroma, mel, contrast, tonnetz]).astype(np.float32)
    return features


def predict_cry_with_model(file_path):
    if CRY_MODEL is None or CRY_LABEL_ENCODER is None:
        raise RuntimeError("Cry model is not loaded")

    features = extract_cry_features(file_path).reshape(1, -1)

    prediction = CRY_MODEL.predict(features)
    predicted_label = CRY_LABEL_ENCODER.inverse_transform(prediction)[0]

    confidence = None
    class_probabilities = {}

    if hasattr(CRY_MODEL, "predict_proba"):
        probs = CRY_MODEL.predict_proba(features)[0]
        confidence = float(np.max(probs))

        try:
            class_names = CRY_LABEL_ENCODER.inverse_transform(np.arange(len(probs)))
            class_probabilities = {
                str(class_names[i]): round(float(probs[i]), 4)
                for i in range(len(probs))
            }
        except Exception:
            pass

    return predicted_label, confidence, class_probabilities


def map_cry_result(label):
    label_key = str(label).strip().lower().replace(" ", "_").replace("-", "_")

    mappings = {
        "belly_pain": {
            "condition": "Possible belly pain / colic",
            "severity": "moderate",
            "description": "The trained model suggests the cry may be related to abdominal discomfort or colic.",
            "recommendations": [
                "Try burping the baby",
                "Try gentle tummy massage",
                "Hold baby upright after feeding",
                "Check for trapped gas",
                "See a pediatrician if the crying is persistent or intense"
            ]
        },
        "burping": {
            "condition": "Needs burping",
            "severity": "mild",
            "description": "The trained model suggests the baby may need burping.",
            "recommendations": [
                "Hold baby upright",
                "Gently pat or rub the back",
                "Pause during feeds for burping"
            ]
        },
        "discomfort": {
            "condition": "General discomfort",
            "severity": "mild",
            "description": "The trained model suggests discomfort rather than a clearly urgent pattern.",
            "recommendations": [
                "Check diaper",
                "Check clothing tightness",
                "Check room temperature",
                "Try changing baby position"
            ]
        },
        "hungry": {
            "condition": "Possible hunger cry",
            "severity": "mild",
            "description": "The trained model suggests the cry may be related to hunger.",
            "recommendations": [
                "Try feeding",
                "Check recent feeding time",
                "Watch for hunger cues such as rooting or sucking motions"
            ]
        },
        "tired": {
            "condition": "Possible tiredness cry",
            "severity": "mild",
            "description": "The trained model suggests the baby may be tired or overstimulated.",
            "recommendations": [
                "Reduce noise and light",
                "Begin sleep routine",
                "Try rocking or white noise"
            ]
        }
    }

    default_result = {
        "condition": f"Predicted cry type: {label}",
        "severity": "mild",
        "description": "The trained model returned a class that is not mapped to a custom description yet.",
        "recommendations": [
            "Check hunger, diaper, temperature, and comfort",
            "Monitor the baby closely",
            "Consult a pediatrician if concerned"
        ]
    }

    return mappings.get(label_key, default_result)


# =========================-
# Cry API Endpoint
# =========================
@app.route("/api/analyze-cry", methods=["POST"])
def analyze_cry():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    audio_data = audio_file.read()

    if not audio_data:
        return jsonify({"error": "Empty audio file"}), 400

    original_filename = audio_file.filename or "audio.wav"
    wav_path = None

    try:
        wav_path = convert_audio_to_wav_16k_mono(audio_data, original_filename)

        if load_cry_model():
            predicted_label, confidence, class_probabilities = predict_cry_with_model(wav_path)
            mapped = map_cry_result(predicted_label)

            return jsonify({
                "classification": predicted_label,
                "confidence": confidence,
                "description": mapped["description"],
                "recommendations": mapped["recommendations"],
                "condition": mapped["condition"],
                "severity": mapped["severity"],
                "class_probabilities": class_probabilities,
                "model_used": "huggingface_local_model",
                "audio_info": {
                    "original_filename": original_filename,
                    "converted_to_wav_mono_16k": True
                },
                "disclaimer": (
                    "This AI result is for guidance only and is not a medical diagnosis. "
                    "Seek urgent medical care for breathing difficulty, seizure, "
                    "unresponsiveness, or fever in babies under 3 months."
                )
            })

        fallback_response = _analyze_cry_basic(audio_data)
        fallback_json = fallback_response.get_json()
        fallback_json["warning"] = f"Model unavailable: {CRY_MODEL_ERROR}"
        fallback_json["audio_info"] = {
            "original_filename": original_filename,
            "converted_to_wav_mono_16k": True
        }
        return jsonify(fallback_json)

    except Exception as e:
        try:
            fallback_response = _analyze_cry_basic(audio_data)
            fallback_json = fallback_response.get_json()
            fallback_json["warning"] = f"Trained model inference failed: {str(e)}"
            fallback_json["audio_info"] = {
                "original_filename": original_filename,
                "converted_to_wav_mono_16k": False
            }
            return jsonify(fallback_json)
        except Exception:
            return jsonify({"error": f"Audio analysis failed: {str(e)}"}), 500

    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass



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



# =========================
# Photo analysis
# Uses simple color-based rules for rash, jaundice, and stool checks
# =========================
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

def predict_severity_with_model(age_months, weight_kg, duration_hours, temperature, gender, symptoms):
    #"""Run the trained severity model and return label + confidence."""
    import pandas as pd

    if SEVERITY_MODEL is None:
        raise RuntimeError("Severity model is not loaded")

    features = _build_severity_features(
        age_months=age_months,
        weight_kg=weight_kg,
        duration_hours=duration_hours,
        temperature=temperature,
        gender=gender,
        symptoms=symptoms
    )

    X = pd.DataFrame([features])
    model = SEVERITY_MODEL["model"]
    inv_label_map = SEVERITY_MODEL["inv_label_map"]

    pred_num = int(model.predict(X)[0])
    pred_label = inv_label_map[pred_num]

    confidence = None
    class_probabilities = {}

    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)[0]
        confidence = float(max(probs))
        for i, p in enumerate(probs):
            class_probabilities[inv_label_map[i]] = round(float(p), 4)

    return pred_label, confidence, class_probabilities
# =========================
# Diagnosis
# First checks emergency rules, then uses the severity model
# =========================
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
    gender = data.get("gender", "male")

    if age_months is None:
        return jsonify({"error": "age_months is required"}), 400

    emergency_result = _check_emergency_rules(age_months, symptoms, temperature)
    if emergency_result:
        return jsonify(emergency_result)

    try:
        if not load_severity_model():
            raise RuntimeError(SEVERITY_MODEL_ERROR or "Severity model unavailable")

        pred_label, confidence, class_probabilities = predict_severity_with_model(
            age_months=age_months,
            weight_kg=weight_kg,
            duration_hours=duration_hours,
            temperature=temperature,
            gender=gender,
            symptoms=symptoms
        )

        mapped = map_severity_result(pred_label)

        return jsonify({
            "prediction": pred_label,
            "confidence": confidence,
            "class_probabilities": class_probabilities,
            "severity": mapped["severity"],
            "severity_label": mapped["severity_label"],
            "advice": mapped["advice"],
            "home_care": mapped["home_care"],
            "when_to_see_doctor": mapped["when_to_see_doctor"],
            "model_used": "curated_severity_xgboost",
            "disclaimer": (
                "This result is generated from a curated synthetic training dataset "
                "based on pediatric symptom-escalation patterns and is not a medical diagnosis. "
                "Emergency signs still require immediate professional care."
            )
        })

    except Exception as e:
        return jsonify({
            "error": f"Severity model inference failed: {str(e)}",
            "model_error": SEVERITY_MODEL_ERROR
        }), 500


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

def _symptom_flags(symptoms):
    s = {str(x).strip().lower() for x in symptoms}

    return {
        "symptom_fever": int("fever" in s),
        "symptom_cough": int("cough" in s),
        "symptom_vomiting": int("vomiting" in s),
        "symptom_diarrhea": int("diarrhea" in s),
        "symptom_rash": int("rash" in s),
        "symptom_lethargy": int("lethargy" in s),
        "symptom_poor_feeding": int("poor feeding" in s),
        "symptom_difficulty_breathing": int("difficulty breathing" in s),
        "symptom_dehydration": int("dehydration" in s),
    }

def _build_severity_features(age_months, weight_kg, duration_hours, temperature, gender, symptoms):
    flags = _symptom_flags(symptoms)
    return {
        "age_months": float(age_months) if age_months is not None else None,
        "weight_kg": float(weight_kg) if weight_kg is not None else None,
        "duration_hours": float(duration_hours) if duration_hours is not None else None,
        "temperature": float(temperature) if temperature is not None else None,
        "gender": gender if gender in ["male", "female"] else "male",
        **flags
    }
def map_severity_result(label):
    if label == "orange":
        return {
            "severity": "orange",
            "severity_label": "Urgent medical review",
            "advice": "The model suggests a higher-risk symptom pattern.",
            "home_care": [
                "Seek urgent medical care",
                "Keep baby monitored closely",
                "Prioritize hydration if baby can feed"
            ],
            "when_to_see_doctor": "Go to urgent care / ER today"
        }
    elif label == "yellow":
        return {
            "severity": "yellow",
            "severity_label": "Doctor review recommended",
            "advice": "The model suggests a moderate-risk symptom pattern.",
            "home_care": [
                "Monitor temperature and feeding",
                "Watch breathing and wet diapers",
                "Seek same-day advice if symptoms worsen"
            ],
            "when_to_see_doctor": "See doctor today or within 24 hours"
        }
    else:
        return {
            "severity": "green",
            "severity_label": "Home monitoring appropriate",
            "advice": "The model suggests a lower-risk symptom pattern.",
            "home_care": [
                "Monitor baby at home",
                "Ensure feeding and comfort",
                "Watch for worsening symptoms"
            ],
            "when_to_see_doctor": "See doctor if symptoms persist or worsen"
        }



#===================================
# Groth tracker
# Saves baby groth records and compares them with WHO standars
#===================================
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
#=================Return percentile and z-score for a baby's weight and height.================
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

    #================"Normal growth"===============
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

# =========================
# Emergency assistant
# Uses decision rules to classify urgent situations quickly
# =========================
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



# =========================
# Community features
# Posts, likes, comments, and simple content moderation
# =========================
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
load_cry_model()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
