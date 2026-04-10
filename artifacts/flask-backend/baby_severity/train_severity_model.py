import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import classification_report, confusion_matrix

from xgboost import XGBClassifier

DATA_PATH = "curated_baby_severity_dataset.csv"
MODEL_PATH = "severity_model.joblib"

TARGET = "severity_label"

df = pd.read_csv(DATA_PATH)

feature_cols = [
    "age_months",
    "weight_kg",
    "duration_hours",
    "temperature",
    "gender",
    "symptom_fever",
    "symptom_cough",
    "symptom_vomiting",
    "symptom_diarrhea",
    "symptom_rash",
    "symptom_lethargy",
    "symptom_poor_feeding",
    "symptom_difficulty_breathing",
    "symptom_dehydration",
]

X = df[feature_cols]
y = df[TARGET]

numeric_features = [
    "age_months",
    "weight_kg",
    "duration_hours",
    "temperature",
    "symptom_fever",
    "symptom_cough",
    "symptom_vomiting",
    "symptom_diarrhea",
    "symptom_rash",
    "symptom_lethargy",
    "symptom_poor_feeding",
    "symptom_difficulty_breathing",
    "symptom_dehydration",
]

categorical_features = ["gender"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", SimpleImputer(strategy="median"), numeric_features),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore"))
        ]), categorical_features),
    ]
)

label_map = {"green": 0, "yellow": 1, "orange": 2}
inv_label_map = {v: k for k, v in label_map.items()}
y_num = y.map(label_map)

X_train, X_test, y_train, y_test = train_test_split(
    X, y_num,
    test_size=0.2,
    random_state=42,
    stratify=y_num
)

model = Pipeline(steps=[
    ("preprocessor", preprocessor),
    ("classifier", XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42
    ))
])

model.fit(X_train, y_train)

pred = model.predict(X_test)
pred_labels = pd.Series(pred).map(inv_label_map)
true_labels = pd.Series(y_test).map(inv_label_map)

print(classification_report(true_labels, pred_labels))
print(confusion_matrix(true_labels, pred_labels, labels=["green", "yellow", "orange"]))

joblib.dump({
    "model": model,
    "label_map": label_map,
    "inv_label_map": inv_label_map,
    "feature_cols": feature_cols,
}, MODEL_PATH)

print(f"Saved model to {MODEL_PATH}")