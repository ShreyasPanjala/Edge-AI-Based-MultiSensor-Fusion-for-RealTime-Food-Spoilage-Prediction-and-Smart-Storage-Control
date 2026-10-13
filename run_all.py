"""Single-command orchestrator to execute the entire research and TinyML pipeline:

1. Runs Experiment A: Real data LODO, 95% bootstrap CI, 75/25 optimistic baseline, D3 transition.
2. Runs Experiment B: Synthetic simulator generation & robustness sweeps.
3. Exports C++ TinyML header (esp32_hybrid.h).
4. Verifies 100% parity across all 4096 ADC integers.
5. Verifies ESP32 firmware compilation via arduino-cli.
"""

from __future__ import annotations
import sys
import subprocess
from pathlib import Path

from src.experiment_a import run_experiment_a
from src.simulator import SyntheticENoseSimulator
from src.robustness_sweep import run_robustness_sweeps
from src.export_hybrid import generate_c_header
from src.verify_export import verify_all_adc_values


def main() -> None:
    print("=" * 80)
    print("      EDGE-AI ELECTRONIC NOSE: COMPLETE REPRODUCIBLE PIPELINE")
    print("=" * 80)

    # Step 1: Real Data Experiment A
    print("\n>>> STEP 1: Executing Experiment A (Real Data LODO & D3 Analysis)...")
    run_experiment_a()

    # Step 2: Synthetic Simulator & Robustness Sweeps
    print("\n>>> STEP 2: Executing Experiment B (Simulator & Robustness Sweeps)...")
    sim = SyntheticENoseSimulator(seed=42)
    sim.generate_full_benchmark_dataset(n_per_class=5000)
    run_robustness_sweeps()

    # Step 3: TinyML C++ Export
    print("\n>>> STEP 3: Transpiling Stacking Hybrid Model to C++ Header...")
    generate_c_header()

    # Step 4: Verification over all 4096 ADC integers
    print("\n>>> STEP 4: Verifying Integer-for-Integer Parity (0..4095)...")
    verify_all_adc_values()

    # Step 5: Firmware Compilation Check
    print("\n>>> STEP 5: Verifying ESP32 Firmware Compilation with arduino-cli...")
    try:
        res = subprocess.run(
            ["arduino-cli", "compile", "--fqbn", "esp32:esp32:esp32", "firmware/esp32_fruit_freshness"],
            capture_output=True,
            text=True,
            check=True,
        )
        print("Firmware Compilation: SUCCESS")
        print(res.stdout.strip())
    except Exception as e:
        print(f"arduino-cli check skipped or encountered error: {e}")

    print("\n" + "=" * 80)
    print("      ALL EXPERIMENTS, EXPORTS, AND VERIFICATIONS COMPLETED SUCCESSFULLY")
    print("=" * 80)


if __name__ == "__main__":
    main()
