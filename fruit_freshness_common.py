from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "Food-Freshness-E-Nose-Dataset" / "AllSamples-Report"

FILES = [
    ("Banana D1.csv", "EARLY"),
    ("Banana D2.csv", "EARLY"),
    ("Banana D3.csv", "EARLY"),
    ("Banana D4.csv", "LATE"),
    ("Banana D5.csv", "LATE"),
]

ALL_SENSOR_COLUMNS = [
    "MQ2",
    "MQ3",
    "MQ4",
    "MQ5",
    "MQ6",
    "MQ7",
    "MQ8",
    "MQ9",
    "MQ135",
]

# The user's ESP32 hardware has MQ135 plus DHT22. This dataset only contains MQ
# gas-sensor columns, so the current hardware-compatible model can use MQ135 only.
MODEL_FEATURES = ["MQ135"]
CLASS_LABELS = ["EARLY", "LATE"]
OUTPUT_LABELS = {"EARLY": "FRESH", "LATE": "SPOILED"}
FINAL_RANDOM_FOREST_CONFIG = {
    "n_estimators": 3,
    "max_depth": 3,
    "min_samples_leaf": 5,
    "random_state": 42,
    "n_jobs": -1,
}


def dataset_columns() -> list[str]:
    sample_file = DATA_DIR / FILES[0][0]
    return pd.read_csv(sample_file, nrows=0).columns.tolist()


def load_datasets(features: list[str] | None = None) -> dict[str, pd.DataFrame]:
    features = features or MODEL_FEATURES
    missing = [feature for feature in features if feature not in dataset_columns()]
    if missing:
        raise ValueError(f"Missing feature columns in dataset: {missing}")

    datasets: dict[str, pd.DataFrame] = {}
    for filename, label in FILES:
        path = DATA_DIR / filename
        df = pd.read_csv(path)
        df = df.sort_values("Ticks").reset_index(drop=True)
        df = df[features].copy()
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        df["Class"] = label
        df["SourceFile"] = filename
        datasets[filename] = df
    return datasets


def load_all_data(features: list[str] | None = None) -> pd.DataFrame:
    return pd.concat(load_datasets(features).values(), ignore_index=True)


def get_model_candidates() -> dict[str, object]:
    return {
        "Random Forest": RandomForestClassifier(
            **FINAL_RANDOM_FOREST_CONFIG,
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=25,
            random_state=42,
        ),
        "Logistic Regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Gaussian NB": GaussianNB(),
    }


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, object]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=CLASS_LABELS,
        average="weighted",
        zero_division=0,
    )
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=CLASS_LABELS),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=CLASS_LABELS,
            zero_division=0,
        ),
    }


def standard_validation(
    model: object,
    features: list[str] | None = None,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict[str, object]:
    features = features or MODEL_FEATURES
    data = load_all_data(features)
    X = data[features].to_numpy()
    y = data["Class"].to_numpy()
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    fitted = clone(model)
    fitted.fit(X_train, y_train)
    pred = fitted.predict(X_test)
    metrics = evaluate_predictions(y_test, pred)
    metrics["model"] = fitted
    metrics["train_rows"] = len(X_train)
    metrics["test_rows"] = len(X_test)
    return metrics


def leave_one_file_out(
    model: object,
    features: list[str] | None = None,
) -> tuple[list[dict[str, object]], float]:
    features = features or MODEL_FEATURES
    datasets = load_datasets(features)
    results: list[dict[str, object]] = []

    for test_file, test_label in FILES:
        test_df = datasets[test_file]
        train_df = pd.concat(
            [df for filename, df in datasets.items() if filename != test_file],
            ignore_index=True,
        )
        X_train = train_df[features].to_numpy()
        y_train = train_df["Class"].to_numpy()
        X_test = test_df[features].to_numpy()
        y_test = test_df["Class"].to_numpy()

        fitted = clone(model)
        fitted.fit(X_train, y_train)
        pred = fitted.predict(X_test)
        metrics = evaluate_predictions(y_test, pred)
        metrics.update(
            {
                "file": test_file,
                "label": test_label,
                "train_rows": len(X_train),
                "test_rows": len(X_test),
            }
        )
        results.append(metrics)

    average_accuracy = float(np.mean([result["accuracy"] for result in results]))
    return results, average_accuracy


def print_dataset_summary(features: list[str] | None = None) -> None:
    features = features or MODEL_FEATURES
    print("Dataset files and binary labels:")
    for filename, label in FILES:
        rows = len(pd.read_csv(DATA_DIR / filename, usecols=features))
        print(f"  {filename}: {label}, {rows} rows")
    print(f"\nCSV columns: {', '.join(dataset_columns())}")
    print(f"Model input features: {', '.join(features)}")
    print("DHT22 temperature/humidity columns: not present in this dataset")


def feature_importance_text(model: object, features: list[str]) -> str:
    estimator = model
    if isinstance(model, Pipeline):
        estimator = model.named_steps.get("model", model)

    if hasattr(estimator, "feature_importances_"):
        pairs = sorted(
            zip(features, estimator.feature_importances_),
            key=lambda item: item[1],
            reverse=True,
        )
        return "\n".join(f"  {name}: {value:.6f}" for name, value in pairs)

    if hasattr(estimator, "coef_"):
        pairs = sorted(
            zip(features, estimator.coef_[0]),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        return "\n".join(f"  {name}: {value:.6f}" for name, value in pairs)

    return "  Not available for this model type"
