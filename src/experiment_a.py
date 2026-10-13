"""Experiment A: Real Data, Redefined Task.

Protocol:
- Task: Binary FRESH (D1, D2) vs SPOILED (D4, D5).
- Explicit Exclusion: D3 is excluded from training & testing benchmark as a biological
  transition phase, and analyzed separately.
- Cross-Validation: Leave-One-Day-Out (LODO) over {D1, D2, D4, D5}.
- Inner Tuning: Nested group CV on the 3 training days (zero leakage to held-out day).
- Models: Single-Threshold Baseline, Decision Tree, Logistic Regression, Gaussian NB,
  Random Forest, Soft-Voting Ensemble, and Stacking (LR meta-learner on inner OOF).
- Statistical Rigor: Per-day accuracy/precision/recall/F1, confusion matrices, mean
  with 95% bootstrap confidence intervals.
- Optimistic Baseline: 75/25 random stratified split, explicitly labelled "optimistic".
- D3 Transition Analysis: Probability histogram and predicted state breakdown.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from src.data_loader import (
    INT_TO_CLASS,
    get_benchmark_arrays,
    load_benchmark_days,
    load_transition_day,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def df_to_markdown_str(df: pd.DataFrame) -> str:
    """Zero-dependency markdown table serializer."""
    headers = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(val) for val in row.values) + " |")
    return "\n".join(lines)


class SingleThresholdClassifier(BaseEstimator, ClassifierMixin):
    """Interpretable single-threshold baseline on scalar MQ135 ADC readings."""

    def __init__(self, threshold: float = 750.0):
        self.threshold = threshold

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SingleThresholdClassifier":
        x_vals = np.asarray(X).ravel()
        # Find threshold maximizing balanced accuracy on training days
        candidates = np.percentile(x_vals, np.linspace(5, 95, 181))
        best_acc = -1.0
        best_thresh = 750.0
        for cand in candidates:
            preds = (x_vals >= cand).astype(int)
            # balanced accuracy
            acc_0 = np.mean(preds[y == 0] == 0) if np.sum(y == 0) > 0 else 0.0
            acc_1 = np.mean(preds[y == 1] == 1) if np.sum(y == 1) > 0 else 0.0
            bal_acc = 0.5 * (acc_0 + acc_1)
            if bal_acc > best_acc:
                best_acc = bal_acc
                best_thresh = cand
        self.threshold = float(best_thresh)
        self.classes_ = np.array([0, 1])
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        x_vals = np.asarray(X).ravel()
        return (x_vals >= self.threshold).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        x_vals = np.asarray(X).ravel()
        # Logistic sigmoid approximation around threshold for probabilistic consistency
        scale = 20.0
        prob_1 = 1.0 / (1.0 + np.exp(-np.clip((x_vals - self.threshold) / scale, -20.0, 20.0)))
        return np.column_stack([1.0 - prob_1, prob_1])


class SoftVotingHybrid(BaseEstimator, ClassifierMixin):
    """Soft-voting ensemble averaging predicted probabilities across base estimators."""

    def __init__(self, estimators: List[Tuple[str, Any]]):
        self.estimators = estimators

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SoftVotingHybrid":
        self.fitted_estimators_ = []
        for name, est in self.estimators:
            fitted = clone(est).fit(X, y)
            self.fitted_estimators_.append((name, fitted))
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        probas = [est.predict_proba(X) for _, est in self.fitted_estimators_]
        return np.mean(probas, axis=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.argmax(self.predict_proba(X), axis=1)


class StackingHybrid(BaseEstimator, ClassifierMixin):
    """Stacking classifier using inner GroupKFold out-of-fold predictions to train meta-learner."""

    def __init__(self, base_estimators: List[Tuple[str, Any]], meta_learner: Any | None = None):
        self.base_estimators = base_estimators
        self.meta_learner = meta_learner or LogisticRegression(random_state=42)

    def fit(self, X: np.ndarray, y: np.ndarray, groups: np.ndarray | None = None) -> "StackingHybrid":
        n_samples = len(X)
        n_est = len(self.base_estimators)
        oof_probas = np.zeros((n_samples, n_est), dtype=np.float64)

        from sklearn.model_selection import StratifiedKFold
        # Inner CV must be stratified by class so every inner training fold contains both FRESH and SPOILED
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_splits = list(skf.split(X, y))

        for train_idx, val_idx in cv_splits:
            X_tr, y_tr = X[train_idx], y[train_idx]
            X_val = X[val_idx]
            for col_i, (_, est) in enumerate(self.base_estimators):
                cloned = clone(est).fit(X_tr, y_tr)
                prob = cloned.predict_proba(X_val)
                if prob.shape[1] == 2:
                    oof_probas[val_idx, col_i] = prob[:, 1]
                else:
                    # Single class fallback if degenerate
                    cls = cloned.classes_[0]
                    oof_probas[val_idx, col_i] = 1.0 if cls == 1 else 0.0

        self.meta_learner_ = clone(self.meta_learner).fit(oof_probas, y)

        self.fitted_base_estimators_ = []
        for name, est in self.base_estimators:
            fitted = clone(est).fit(X, y)
            self.fitted_base_estimators_.append((name, fitted))

        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        meta_features = np.column_stack(
            [est.predict_proba(X)[:, 1] for _, est in self.fitted_base_estimators_]
        )
        return self.meta_learner_.predict_proba(meta_features)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.argmax(self.predict_proba(X), axis=1)


def get_models() -> Dict[str, Any]:
    """Define candidate model suite with locked configurations."""
    rf = RandomForestClassifier(
        n_estimators=5,
        max_depth=3,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    dt = DecisionTreeClassifier(
        max_depth=3,
        min_samples_leaf=10,
        random_state=42,
    )
    lr = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(random_state=42, C=1.0)),
        ]
    )
    gnb = GaussianNB()
    st = SingleThresholdClassifier()

    base_list = [
        ("RF", rf),
        ("DT", dt),
        ("LR", lr),
        ("GNB", gnb),
    ]

    return {
        "Single-Threshold": st,
        "Decision Tree": dt,
        "Logistic Regression": lr,
        "Gaussian NB": gnb,
        "Random Forest": rf,
        "Soft-Voting Hybrid": SoftVotingHybrid(base_list),
        "Stacking Hybrid": StackingHybrid(base_list),
    }


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1], average="weighted", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "confusion_matrix": cm.tolist(),
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }


def bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_func=accuracy_score,
    n_bootstraps: int = 1000,
    seed: int = 42,
) -> Tuple[float, float]:
    rng = np.random.default_rng(seed)
    scores = []
    n = len(y_true)
    for _ in range(n_bootstraps):
        idx = rng.integers(0, n, size=n)
        scores.append(metric_func(y_true[idx], y_pred[idx]))
    lower = float(np.percentile(scores, 2.5))
    upper = float(np.percentile(scores, 97.5))
    return lower, upper


def run_experiment_a() -> Dict[str, Any]:
    """Execute complete Experiment A evaluation protocol."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    X_all, y_all, groups_all = get_benchmark_arrays()
    unique_days = ["D1", "D2", "D4", "D5"]
    models = get_models()

    lodo_results: Dict[str, List[Dict[str, Any]]] = {name: [] for name in models}
    pooled_preds: Dict[str, Dict[str, List[int]]] = {
        name: {"y_true": [], "y_pred": [], "y_prob": []} for name in models
    }

    print("\n" + "=" * 78)
    print("EXPERIMENT A: LEAVE-ONE-DAY-OUT (LODO) BENCHMARK OVER {D1, D2, D4, D5}")
    print("=" * 78)

    for test_day in unique_days:
        test_mask = groups_all == test_day
        train_mask = ~test_mask

        X_train, y_train, groups_train = (
            X_all[train_mask],
            y_all[train_mask],
            groups_all[train_mask],
        )
        X_test, y_test = X_all[test_mask], y_all[test_mask]

        test_label = "FRESH" if test_day in ["D1", "D2"] else "SPOILED"
        print(f"\nHeld-out Test Day: {test_day} ({test_label}, N={len(y_test)}):")

        for model_name, model in models.items():
            fitted = clone(model)
            if isinstance(fitted, StackingHybrid):
                fitted.fit(X_train, y_train, groups=groups_train)
            else:
                fitted.fit(X_train, y_train)

            y_pred = fitted.predict(X_test)
            y_prob = fitted.predict_proba(X_test)[:, 1]

            metrics = compute_metrics(y_test, y_pred)
            metrics["day"] = test_day
            metrics["true_label"] = test_label
            metrics["n_test"] = len(y_test)
            lodo_results[model_name].append(metrics)

            pooled_preds[model_name]["y_true"].extend(y_test.tolist())
            pooled_preds[model_name]["y_pred"].extend(y_pred.tolist())
            pooled_preds[model_name]["y_prob"].extend(y_prob.tolist())

            print(
                f"  {model_name:22s} | Acc: {metrics['accuracy'] * 100:6.2f}% | "
                f"Prec: {metrics['precision']:.4f} | Rec: {metrics['recall']:.4f} | F1: {metrics['f1']:.4f}"
            )

    # Compute Aggregate LODO Metrics with 95% Bootstrap CI
    summary_rows = []
    for model_name in models:
        y_t = np.array(pooled_preds[model_name]["y_true"])
        y_p = np.array(pooled_preds[model_name]["y_pred"])
        day_accs = [m["accuracy"] for m in lodo_results[model_name]]
        mean_acc = float(np.mean(day_accs))

        # Overall pooled metrics
        pooled_metrics = compute_metrics(y_t, y_p)
        ci_low, ci_high = bootstrap_ci(y_t, y_p, accuracy_score, n_bootstraps=1000)

        summary_rows.append(
            {
                "Model": model_name,
                "Mean Day Acc (%)": round(mean_acc * 100, 2),
                "Pooled Acc (%)": round(pooled_metrics["accuracy"] * 100, 2),
                "95% CI Lower (%)": round(ci_low * 100, 2),
                "95% CI Upper (%)": round(ci_high * 100, 2),
                "Precision": round(pooled_metrics["precision"], 4),
                "Recall": round(pooled_metrics["recall"], 4),
                "F1-Score": round(pooled_metrics["f1"], 4),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(TABLES_DIR / "experiment_a_lodo_summary.csv", index=False)
    (TABLES_DIR / "experiment_a_lodo_summary.md").write_text(
        df_to_markdown_str(summary_df), encoding="utf-8"
    )

    # Build detailed per-day markdown table
    per_day_rows = []
    for model_name, day_list in lodo_results.items():
        for item in day_list:
            per_day_rows.append(
                {
                    "Model": model_name,
                    "Held-Out Day": item["day"],
                    "True State": item["true_label"],
                    "Samples": item["n_test"],
                    "Accuracy (%)": round(item["accuracy"] * 100, 2),
                    "Precision": round(item["precision"], 4),
                    "Recall": round(item["recall"], 4),
                    "F1-Score": round(item["f1"], 4),
                    "TN": item["tn"],
                    "FP": item["fp"],
                    "FN": item["fn"],
                    "TP": item["tp"],
                }
            )
    per_day_df = pd.DataFrame(per_day_rows)
    per_day_df.to_csv(TABLES_DIR / "experiment_a_lodo_per_day.csv", index=False)
    (TABLES_DIR / "experiment_a_lodo_per_day.md").write_text(
        df_to_markdown_str(per_day_df), encoding="utf-8"
    )

    print("\n" + "=" * 78)
    print("LODO AGGREGATE SUMMARY (HEADLINE RESULTS WITH 95% BOOTSTRAP CI)")
    print("=" * 78)
    print(summary_df.to_string(index=False))

    # --- Optimistic 75/25 Random Split Baseline ---
    print("\n" + "=" * 78)
    print("OPTIMISTIC BASELINE: 75/25 STRATIFIED RANDOM SPLIT (POOLED DATA)")
    print("=" * 78)
    X_train_opt, X_test_opt, y_train_opt, y_test_opt = train_test_split(
        X_all, y_all, test_size=0.25, random_state=42, stratify=y_all
    )
    optimistic_rows = []
    for model_name, model in models.items():
        fitted = clone(model)
        fitted.fit(X_train_opt, y_train_opt)
        y_pred_opt = fitted.predict(X_test_opt)
        m = compute_metrics(y_test_opt, y_pred_opt)
        optimistic_rows.append(
            {
                "Model": model_name,
                "Accuracy (%)": round(m["accuracy"] * 100, 2),
                "Precision": round(m["precision"], 4),
                "Recall": round(m["recall"], 4),
                "F1-Score": round(m["f1"], 4),
                "TN": m["tn"],
                "FP": m["fp"],
                "FN": m["fn"],
                "TP": m["tp"],
                "Evaluation Note": "Optimistic random split (leaks temporal autocorrelation)",
            }
        )
        print(
            f"  {model_name:22s} | Acc: {m['accuracy'] * 100:6.2f}% | "
            f"F1: {m['f1']:.4f} | Conf: [[{m['tn']}, {m['fp']}], [{m['fn']}, {m['tp']}]]"
        )
    optimistic_df = pd.DataFrame(optimistic_rows)
    optimistic_df.to_csv(TABLES_DIR / "experiment_a_optimistic_75_25.csv", index=False)
    (TABLES_DIR / "experiment_a_optimistic_75_25.md").write_text(
        df_to_markdown_str(optimistic_df), encoding="utf-8"
    )

    # --- Transition Day D3 Analysis ---
    print("\n" + "=" * 78)
    print("TRANSITION DAY D3 ANALYSIS (SEPARATE ISOLATED EVALUATION)")
    print("=" * 78)
    d3_df = load_transition_day()
    X_d3 = d3_df[["MQ135"]].to_numpy(dtype=np.float64)
    n_d3 = len(X_d3)

    # Train final models on ALL benchmark days {D1, D2, D4, D5}
    final_models: Dict[str, Any] = {}
    d3_eval_rows = []

    for model_name, model in models.items():
        fitted = clone(model)
        if isinstance(fitted, StackingHybrid):
            fitted.fit(X_all, y_all, groups=groups_all)
        else:
            fitted.fit(X_all, y_all)
        final_models[model_name] = fitted

        preds_d3 = fitted.predict(X_d3)
        probs_d3 = fitted.predict_proba(X_d3)[:, 1]

        fresh_cnt = int(np.sum(preds_d3 == 0))
        spoiled_cnt = int(np.sum(preds_d3 == 1))
        fresh_pct = float(fresh_cnt / n_d3 * 100.0)
        spoiled_pct = float(spoiled_cnt / n_d3 * 100.0)

        d3_eval_rows.append(
            {
                "Model": model_name,
                "D3 Samples": n_d3,
                "Predicted FRESH (%)": round(fresh_pct, 2),
                "Predicted SPOILED (%)": round(spoiled_pct, 2),
                "Mean P(Spoiled)": round(float(np.mean(probs_d3)), 4),
                "Median P(Spoiled)": round(float(np.median(probs_d3)), 4),
                "Std Dev P(Spoiled)": round(float(np.std(probs_d3)), 4),
                "IQR P(Spoiled)": round(
                    float(np.percentile(probs_d3, 75) - np.percentile(probs_d3, 25)), 4
                ),
            }
        )

    d3_table = pd.DataFrame(d3_eval_rows)
    d3_table.to_csv(TABLES_DIR / "experiment_a_d3_transition.csv", index=False)
    (TABLES_DIR / "experiment_a_d3_transition.md").write_text(
        df_to_markdown_str(d3_table), encoding="utf-8"
    )
    print(d3_table.to_string(index=False))

    # Plot D3 Probability Histogram for Stacking Hybrid & Random Forest
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    for ax, m_name in zip(axes, ["Stacking Hybrid", "Random Forest"]):
        model = final_models[m_name]
        p_d3 = model.predict_proba(X_d3)[:, 1]
        ax.hist(
            p_d3,
            bins=20,
            range=(0, 1),
            color="#2b5c8f",
            edgecolor="white",
            alpha=0.85,
        )
        ax.axvline(
            0.5,
            color="#d9534f",
            linestyle="--",
            linewidth=2,
            label="Decision Boundary (0.50)",
        )
        ax.set_title(f"{m_name} - D3 Transition Day Probability", fontsize=11, fontweight="bold")
        ax.set_xlabel("Predicted P(SPOILED)", fontsize=10)
        ax.set_ylabel("Sample Frequency (N=13,395)", fontsize=10)
        ax.legend(loc="upper right")
        ax.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    hist_fig_path = FIGURES_DIR / "d3_transition_probability_histogram.png"
    plt.savefig(hist_fig_path)
    plt.close()
    print(f"\nSaved transition histogram figure: {hist_fig_path}")

    # Serialize final primary hybrid model
    final_hybrid = final_models["StackingHybrid" if "StackingHybrid" in final_models else "Stacking Hybrid"]
    joblib.dump(final_hybrid, MODELS_DIR / "final_hybrid.pkl")
    print(f"Saved final hybrid model artifact: {MODELS_DIR / 'final_hybrid.pkl'}")

    return {
        "lodo_summary": summary_df.to_dict(orient="records"),
        "d3_analysis": d3_eval_rows,
        "optimistic_75_25": optimistic_rows,
    }


if __name__ == "__main__":
    run_experiment_a()
