"""Robustness sweeps using the synthetic simulator.

Sweeps evaluated:
1. Class Overlap Sweep: Shifts class means to vary distribution overlap from 0% to 100%.
2. Sensor Drift Sweep: Tests baseline stability across severe drift rates.
3. Noise Scale Sweep: Evaluates boundary degradation under increasing AR(1) noise variance.

DISCLAIMER: All experiments in this script use SIMULATED DATA.
This is used solely for algorithmic stress testing and sensitivity profiling.
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from src.experiment_a import get_models, df_to_markdown_str
from src.simulator import SyntheticENoseSimulator

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"


def run_robustness_sweeps() -> pd.DataFrame:
    """Execute robustness sweeps across overlap, noise, and drift."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 78)
    print("EXPERIMENT B: SIMULATED ROBUSTNESS SWEEPS (CLEARLY LABELLED: SIMULATED DATA)")
    print("=" * 78)

    models = get_models()
    evaluated_models = ["Single-Threshold", "Random Forest", "Stacking Hybrid"]

    # 1. Class Overlap Sweep
    overlap_results = []
    # Delta mean separation from 500 down to 0
    delta_separations = [500, 400, 300, 200, 150, 100, 50, 20, 0]

    for delta in delta_separations:
        sim = SyntheticENoseSimulator(
            fresh_mean=600.0,
            spoiled_mean=600.0 + delta,
            fresh_std=80.0,
            spoiled_std=80.0,
            seed=42 + delta,
        )
        fresh_df = sim.generate_class_series("FRESH", 2500)
        spoiled_df = sim.generate_class_series("SPOILED", 2500)
        combined = pd.concat([fresh_df, spoiled_df], ignore_index=True)

        X = combined[["MQ135"]].to_numpy()
        y = (combined["Class"] == "SPOILED").astype(int).to_numpy()

        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )

        # Theoretical overlap percentage estimation
        # For equal std (sigma=80), distance between means = delta / sigma
        d_prime = delta / 80.0
        # Overlap area between two normal distributions
        from scipy.stats import norm
        overlap_pct = float(2.0 * norm.cdf(-d_prime / 2.0) * 100.0)

        row = {
            "Sweep Type": "Class Overlap",
            "Mean Separation (Delta ADC)": delta,
            "Theoretical Overlap (%)": round(overlap_pct, 2),
            "Noise Scale": 1.0,
            "Drift Scale": 1.0,
        }

        for m_name in evaluated_models:
            clf = models[m_name]
            clf.fit(X_tr, y_tr)
            preds = clf.predict(X_te)
            acc = float(accuracy_score(y_te, preds) * 100.0)
            row[f"{m_name} Acc (%)"] = round(acc, 2)

        overlap_results.append(row)
        print(
            f"  Delta={delta:3d} ADC | Overlap={overlap_pct:5.1f}% | "
            + " | ".join(f"{m}: {row[f'{m} Acc (%)']:.1f}%" for m in evaluated_models)
        )

    # Plot Accuracy vs Overlap
    overlap_df = pd.DataFrame(overlap_results)
    plt.figure(figsize=(8, 5), dpi=300)
    for m_name in evaluated_models:
        plt.plot(
            overlap_df["Theoretical Overlap (%)"],
            overlap_df[f"{m_name} Acc (%)"],
            marker="o",
            linewidth=2,
            label=m_name,
        )

    plt.title("Simulated Data: Classification Accuracy vs. Class Overlap", fontsize=12, fontweight="bold")
    plt.xlabel("Distribution Overlap Area (%) [Simulated]", fontsize=11)
    plt.ylabel("Test Accuracy (%) [Simulated Data]", fontsize=11)
    plt.axhline(50.0, color="gray", linestyle=":", label="Random Guess (50%)")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right")
    plt.tight_layout()

    fig_path = FIGURES_DIR / "simulator_accuracy_vs_overlap.png"
    plt.savefig(fig_path)
    plt.close()
    print(f"\nSaved Accuracy vs Overlap figure: {fig_path}")

    # 2. Noise Scale Sweep
    noise_results = []
    noise_scales = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    for n_scale in noise_scales:
        sim = SyntheticENoseSimulator(seed=int(n_scale * 100))
        fresh_df = sim.generate_class_series("FRESH", 2500, noise_scale=n_scale)
        spoiled_df = sim.generate_class_series("SPOILED", 2500, noise_scale=n_scale)
        combined = pd.concat([fresh_df, spoiled_df], ignore_index=True)

        X = combined[["MQ135"]].to_numpy()
        y = (combined["Class"] == "SPOILED").astype(int).to_numpy()
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )

        row = {
            "Sweep Type": "Noise Scale",
            "Mean Separation (Delta ADC)": 516,
            "Theoretical Overlap (%)": round(float(n_scale * 1.5), 2),
            "Noise Scale": n_scale,
            "Drift Scale": 1.0,
        }
        for m_name in evaluated_models:
            clf = models[m_name]
            clf.fit(X_tr, y_tr)
            preds = clf.predict(X_te)
            acc = float(accuracy_score(y_te, preds) * 100.0)
            row[f"{m_name} Acc (%)"] = round(acc, 2)
        noise_results.append(row)

    # 3. Drift Scale Sweep
    drift_results = []
    drift_scales = [0.0, 1.0, 2.0, 5.0, 10.0, 20.0]
    for d_scale in drift_scales:
        sim = SyntheticENoseSimulator(seed=int(d_scale * 10) + 7)
        fresh_df = sim.generate_class_series("FRESH", 2500, drift_scale=d_scale)
        spoiled_df = sim.generate_class_series("SPOILED", 2500, drift_scale=d_scale)
        combined = pd.concat([fresh_df, spoiled_df], ignore_index=True)

        X = combined[["MQ135"]].to_numpy()
        y = (combined["Class"] == "SPOILED").astype(int).to_numpy()
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )

        row = {
            "Sweep Type": "Sensor Drift",
            "Mean Separation (Delta ADC)": 516,
            "Theoretical Overlap (%)": 0.5,
            "Noise Scale": 1.0,
            "Drift Scale": d_scale,
        }
        for m_name in evaluated_models:
            clf = models[m_name]
            clf.fit(X_tr, y_tr)
            preds = clf.predict(X_te)
            acc = float(accuracy_score(y_te, preds) * 100.0)
            row[f"{m_name} Acc (%)"] = round(acc, 2)
        drift_results.append(row)

    # Consolidate all sweep results into a single table
    all_sweeps_df = pd.concat(
        [
            pd.DataFrame(overlap_results),
            pd.DataFrame(noise_results),
            pd.DataFrame(drift_results),
        ],
        ignore_index=True,
    )

    all_sweeps_df.to_csv(TABLES_DIR / "simulator_robustness_sweep.csv", index=False)
    md_content = (
        "# Simulated Data: Robustness Sweep under Parametric Noise, Drift, and Class Overlap\n\n"
        "> **DISCLAIMER: All values in this table are generated from the synthetic simulator (`src/simulator.py`). "
        "They evaluate algorithmic sensitivity and MUST NOT be cited as physical sensor accuracy.**\n\n"
        + df_to_markdown_str(all_sweeps_df)
    )
    (TABLES_DIR / "simulator_robustness_sweep.md").write_text(md_content, encoding="utf-8")
    print(f"Saved simulator robustness table: {TABLES_DIR / 'simulator_robustness_sweep.md'}")
    return all_sweeps_df


if __name__ == "__main__":
    run_robustness_sweeps()
