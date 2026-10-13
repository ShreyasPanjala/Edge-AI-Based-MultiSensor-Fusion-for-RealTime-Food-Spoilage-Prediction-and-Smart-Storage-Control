"""Experiment B: Fully Synthetic Sensor Simulator.

PURPOSE:
- Simulates MQ135-like time-series response with configurable GMM base distribution,
  AR(1) temporal autocorrelation noise, slow baseline drift, and sensor-to-sensor gain variation.
- Generates optional simulated DHT22 environmental columns (Temperature, Humidity) with an
  explicit cross-sensitivity model, labelled "simulated assumption".
- Strict isolation: every record contains is_synthetic=1, generator metadata, parameters, and seed.
- WARNING: This module is used solely for pipeline testing, C++ export verification,
  and robustness sweeps. Simulator accuracy is NEVER reported as real sensor performance.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Tuple, Any

import numpy as np
import pandas as pd

SYNTHETIC_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


class SyntheticENoseSimulator:
    """Generates synthetic E-Nose time-series data fitted from empirical statistics."""

    def __init__(
        self,
        fresh_mean: float = 577.6,
        fresh_std: float = 75.0,
        spoiled_mean: float = 1094.3,
        spoiled_std: float = 95.8,
        ar1_phi: float = 0.88,
        ar1_sigma: float = 12.0,
        drift_rate: float = 0.0005,
        gain_std: float = 0.03,
        temp_cross_sens: float = 0.003,
        humidity_cross_sens: float = 0.002,
        seed: int = 42,
    ):
        self.fresh_mean = fresh_mean
        self.fresh_std = fresh_std
        self.spoiled_mean = spoiled_mean
        self.spoiled_std = spoiled_std
        self.ar1_phi = ar1_phi
        self.ar1_sigma = ar1_sigma
        self.drift_rate = drift_rate
        self.gain_std = gain_std
        self.temp_cross_sens = temp_cross_sens
        self.humidity_cross_sens = humidity_cross_sens
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_class_series(
        self,
        class_label: str,
        n_samples: int,
        mean_shift: float = 0.0,
        noise_scale: float = 1.0,
        drift_scale: float = 1.0,
    ) -> pd.DataFrame:
        """Generate a single class time series with AR(1) noise, drift, and DHT22 cross-sensitivity."""
        base_mean = (self.fresh_mean if class_label == "FRESH" else self.spoiled_mean) + mean_shift
        base_std = (self.fresh_std if class_label == "FRESH" else self.spoiled_std) * noise_scale

        # Sensor gain variation
        sensor_gain = float(self.rng.normal(1.0, self.gain_std))

        # Base gas emission concentration
        base_signals = self.rng.normal(base_mean, base_std, size=n_samples)

        # Autoregressive AR(1) colored noise: x_t = phi * x_{t-1} + eps_t
        ar_noise = np.zeros(n_samples, dtype=np.float64)
        innovations = self.rng.normal(0.0, self.ar1_sigma * noise_scale, size=n_samples)
        for t in range(1, n_samples):
            ar_noise[t] = self.ar1_phi * ar_noise[t - 1] + innovations[t]

        # Slow sensor baseline drift
        t_steps = np.arange(n_samples)
        drift = self.drift_rate * drift_scale * t_steps

        # Simulated ambient DHT22 environment (T in C, RH in %)
        temperatures = self.rng.normal(24.0, 1.5, size=n_samples)
        humidities = self.rng.normal(60.0, 5.0, size=n_samples)

        # Cross-sensitivity effect (simulated assumption)
        env_modulation = 1.0 + (
            self.temp_cross_sens * (temperatures - 20.0)
            + self.humidity_cross_sens * (humidities - 55.0)
        )

        # Raw ADC reading
        raw_adc = (base_signals * env_modulation * sensor_gain) + ar_noise + drift
        clipped_adc = np.clip(np.round(raw_adc), 0, 4095).astype(int)

        params_meta = {
            "fresh_mean": self.fresh_mean,
            "spoiled_mean": self.spoiled_mean,
            "mean_shift": mean_shift,
            "noise_scale": noise_scale,
            "drift_scale": drift_scale,
            "sensor_gain": round(sensor_gain, 4),
        }

        df = pd.DataFrame(
            {
                "Ticks": np.arange(1000, 1000 + n_samples * 2000, 2000),
                "MQ135": clipped_adc,
                "Temperature_C_sim": np.round(temperatures, 2),
                "Humidity_RH_sim": np.round(humidities, 2),
                "Class": class_label,
                "is_synthetic": 1,
                "generator": "SyntheticENose_v1",
                "parameters": json.dumps(params_meta),
                "seed": self.seed,
                "notes": "Simulated assumption: DHT22 cross-sensitivity added to MQ135",
            }
        )
        return df

    def generate_full_benchmark_dataset(
        self, n_per_class: int = 10000, filename: str = "synthetic_enose_benchmark.csv"
    ) -> pd.DataFrame:
        """Generate balanced synthetic benchmark for end-to-end pipeline validation."""
        SYNTHETIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
        fresh_df = self.generate_class_series("FRESH", n_per_class)
        spoiled_df = self.generate_class_series("SPOILED", n_per_class)
        combined = pd.concat([fresh_df, spoiled_df], ignore_index=True)
        out_path = SYNTHETIC_DATA_DIR / filename
        combined.to_csv(out_path, index=False)
        return combined


if __name__ == "__main__":
    sim = SyntheticENoseSimulator(seed=101)
    df = sim.generate_full_benchmark_dataset(n_per_class=5000)
    print(f"Generated synthetic dataset: {len(df)} rows.")
    print(f"Columns: {list(df.columns)}")
    print(df.groupby('Class')['MQ135'].describe())
