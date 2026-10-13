"""Data loader for real Banana E-Nose datasets.

Supports explicit experimental protocols:
- Experiment A (Headline Task): Binary FRESH (D1, D2) vs SPOILED (D4, D5), excluding D3.
- Transition Analysis: Isolated evaluation on D3 without polluting the primary benchmark.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

REAL_FILES: Dict[str, Dict[str, str]] = {
    "Banana D1.csv": {"day": "D1", "class": "FRESH", "role": "benchmark"},
    "Banana D2.csv": {"day": "D2", "class": "FRESH", "role": "benchmark"},
    "Banana D3.csv": {"day": "D3", "class": "TRANSITION", "role": "transition"},
    "Banana D4.csv": {"day": "D4", "class": "SPOILED", "role": "benchmark"},
    "Banana D5.csv": {"day": "D5", "class": "SPOILED", "role": "benchmark"},
}

CLASS_TO_INT = {"FRESH": 0, "SPOILED": 1}
INT_TO_CLASS = {0: "FRESH", 1: "SPOILED"}


def load_day_dataframe(filename: str) -> pd.DataFrame:
    """Load a single CSV file, ensuring numeric typing and sorting by time ticks."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    df = pd.read_csv(filepath)
    if "Ticks" in df.columns:
        df = df.sort_values("Ticks").reset_index(drop=True)
    df["MQ135"] = pd.to_numeric(df["MQ135"], errors="coerce")
    df = df.dropna(subset=["MQ135"]).copy()
    meta = REAL_FILES[filename]
    df["Day"] = meta["day"]
    df["Class"] = meta["class"]
    df["SourceFile"] = filename
    return df


def load_benchmark_days() -> Dict[str, pd.DataFrame]:
    """Load the four benchmark days {D1, D2, D4, D5} for Experiment A."""
    return {
        meta["day"]: load_day_dataframe(fname)
        for fname, meta in REAL_FILES.items()
        if meta["role"] == "benchmark"
    }


def load_transition_day() -> pd.DataFrame:
    """Load Day 3 exclusively for transition phase analysis."""
    return load_day_dataframe("Banana D3.csv")


def get_benchmark_arrays() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return X (N, 1), y (N,), and day_groups (N,) for all benchmark observations."""
    dfs = load_benchmark_days()
    combined = pd.concat(dfs.values(), ignore_index=True)
    X = combined[["MQ135"]].to_numpy(dtype=np.float64)
    y = np.array([CLASS_TO_INT[c] for c in combined["Class"]], dtype=np.int64)
    groups = combined["Day"].to_numpy()
    return X, y, groups
