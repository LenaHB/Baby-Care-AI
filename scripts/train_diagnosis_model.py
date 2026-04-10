import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer

WHO_DATA = {
    'disease': [
        'Acute Respiratory Infection', 'Diarrhea', 'Malaria', 'Measles',
        'Pneumonia', 'Bronchiolitis', 'Gastroenteritis', 'Chickenpox',
        'Hand Foot Mouth Disease', 'Allergic Rhinitis', 'Asthma',
        'Urinary Tract Infection', 'Otitis Media', 'Dengue Fever'
    ],
    'common_symptoms': [
        'fever,cough,rapid_breathing',
        'diarrhea,vomiting,dehydration',
        'fever,chills,sweating',
        'fever,rash,cough,conjunctivitis',
        'fever,cough,chest_pain,difficulty_breathing',
        'cough,wheezing,rapid_breathing',
        'nausea,vomiting,diarrhea,abdominal_pain',
        'rash,fever,itching,blisters',
        'rash,fever,sore_throat,blisters',
        'sneezing,runny_nose,itchy_eyes',
        'wheezing,cough,shortness_breath',
        'fever,painful_urination,abdominal_pain',
        'ear_pain,fever,irritability',
        'fever,headache,muscle_pain,rash'
    ],
    'severity': ['medium', 'high', 'high', 'high', 'critical', 'high', 'medium', 'medium', 'low', 'low', 'high', 'medium', 'medium', 'high'],
    'age_group': ['0-5', '0-5', 'all', '1-5', '0-5', '0-2', 'all', '1-10', '1-5', 'all', 'all', '0-5', '0-5', 'all']
}

MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'artifacts', 'flask-backend', 'model')


def ensure_model_dir():
    os.makedirs(MODEL_DIR, exist_ok=True)


def build_data():
    df = pd.DataFrame(WHO_DATA)
    df['symptoms'] = df['common_symptoms'].str.split(',')
    df['age_group_cat'] = df['age_group']
    return df


def train():
    df = build_data()

    mlb = MultiLabelBinarizer()
    X_symptom = mlb.fit_transform(df['symptoms'])

    age_categories = sorted(df['age_group'].unique())
    X_age = pd.get_dummies(df['age_group']).reindex(columns=age_categories, fill_value=0)

    X = np.hstack([X_symptom, X_age.values])

    disease_encoder = LabelEncoder()
    y = disease_encoder.fit_transform(df['disease'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print('Classification report for model:')
    print(classification_report(y_test, y_pred, target_names=disease_encoder.classes_))

    ensure_model_dir()

    joblib.dump(model, os.path.join(MODEL_DIR, 'diagnose_model.joblib'))
    joblib.dump(mlb, os.path.join(MODEL_DIR, 'symptom_mlb.joblib'))
    joblib.dump(age_categories, os.path.join(MODEL_DIR, 'age_categories.joblib'))
    joblib.dump(disease_encoder, os.path.join(MODEL_DIR, 'disease_encoder.joblib'))

    print('Saved model artifacts to', MODEL_DIR)


if __name__ == '__main__':
    train()
