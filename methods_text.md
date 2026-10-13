# Methodology: Edge-AI Electronic Nose for Non-Destructive Fruit Spoilage Detection

## 1. Problem Formulation and Protocol Definition

We define the primary objective as the automated, non-destructive discrimination between **FRESH** and **SPOILED** post-harvest fruit states using real-time metal-oxide semiconductor (MOS) volatile gas sensing on edge hardware. 

### Explicit Exclusion of Transition Phase (Day 3)
In the source benchmark (*Food-Freshness-E-Nose-Dataset*), sensor recordings are captured sequentially across five consecutive ripening days ($D_1$ through $D_5$):
- $D_1$ and $D_2$ represent unequivocal, edible freshness (green to ripe stages).
- $D_4$ and $D_5$ represent distinct post-climacteric decay (overripe to structural decomposition).
- $D_3$ captures the metabolic climacteric ripening transition, characterized by a rapid surge in volatile organic compounds (esters, ethanol, ethylene derivatives) prior to visible brown necrosis.

Forcing an arbitrary binary boundary across $D_3$ distorts the ground truth of clean physiological states. Therefore, as an **explicit protocol design choice**, $D_3$ is excluded from the primary training and testing benchmark ($N = 69,110$ observations across $\{D_1, D_2, D_4, D_5\}$). Instead, $D_3$ ($N = 13,395$ observations) is reserved for an isolated **transition phase analysis**, evaluating how trained classifiers respond to pre-symptomatic volatile accumulation without contaminating primary validation metrics.

---

## 2. Hardware Architecture and Embedded Acquisition

The edge monitoring node comprises:
1. **Microcontroller Unit (MCU)**: Espressif ESP32 (Xtensa dual-core 32-bit LX6 microcontroller running at 240 MHz, 520 KB SRAM, 4 MB Flash).
2. **Volatile Gas Sensor**: MQ135 Air Quality Sensor connected to an analog-to-digital converter (ADC) channel on **GPIO 34**. The sensor utilizes a doped Tin Dioxide ($SnO_2$) ceramic sensing layer with broad sensitivity to volatile organic compounds, ammonia, ethanol, and carbon dioxide.
3. **Environmental Sensor**: DHT22 (AM2302) capacitive humidity and thermistor module connected to **GPIO 4**, operating at a 2-second acquisition cycle. Because the public benchmark dataset lacks ambient thermohygrometric channels, DHT22 measurements are logged to serial telemetry for environmental context and display, but are strictly excluded from the ML feature vector to prevent uncalibrated synthetic bias.
4. **Actuators**: An alert LED on **GPIO 13** (driven HIGH upon spoilage classification) and an active-low audible buzzer on **GPIO 12** (driven LOW upon spoilage classification).

---

## 3. Experimental Validation Protocol

### A. Leave-One-Day-Out (LODO) Cross-Validation
To simulate deployment across unseen batches and environmental cycles, we adopt a 4-fold **Leave-One-Day-Out (LODO)** evaluation:
$$\mathcal{D} = \{D_1, D_2, D_4, D_5\}$$
In fold $k$, all observations from day $D_k$ are held out as the test set, while the remaining three days constitute the training set $\mathcal{D}_{\text{train}} = \mathcal{D} \setminus \{D_k\}$. Hyperparameters and meta-learners are tuned strictly within $\mathcal{D}_{\text{train}}$ via nested stratified cross-validation, guaranteeing zero leakage to the held-out evaluation day.

### B. Optimistic Random Split Baseline
To benchmark the effect of evaluation methodology, we simultaneously train models on a conventional **75/25 stratified holdout split** across pooled observations. We explicitly document this split as "optimistic," demonstrating how random splitting across temporally correlated sensor time-series inflates accuracy metrics toward 100% by leaking identical minute-by-minute baseline drift between training and testing sets.

### C. Statistical Significance via Bootstrap Confidence Intervals
To assess metric stability across sample sets, we compute 95% non-parametric bootstrap confidence intervals (1,000 resamples with replacement) over the aggregated out-of-fold predictions.

---

## 4. Machine Learning and Hybrid Architectures

We evaluate five base estimators and two hybrid architectures on raw 12-bit ADC features ($x \in [0, 4095]$):
1. **Single-Threshold Baseline**: An optimal scalar boundary $\tau$ chosen by maximizing balanced accuracy on training days.
2. **Decision Tree (DT)**: Constrained tree depth ($\le 3$) and leaf regularization ($\ge 10$) to mitigate sensor noise overfitting.
3. **Logistic Regression (LR)**: Standardized linear sigmoid classifier ($C = 1.0$).
4. **Gaussian Naive Bayes (GNB)**: Maximum-likelihood Gaussian density estimator.
5. **Random Forest (RF)**: Ensemble of 5 shallow decision trees with bagging.
6. **Soft-Voting Hybrid**: Averages posterior class probabilities across DT, LR, GNB, and RF:
   $$P_{\text{vote}}(y = 1 \mid x) = \frac{1}{M} \sum_{m=1}^{M} P_m(y = 1 \mid x)$$
7. **Stacking Hybrid**: Employs an out-of-fold (OOF) cross-validated Logistic Regression meta-learner trained on the 5-fold inner predictions of base estimators.

---

## 5. Synthetic Sensor Simulator (Experiment B)

To stress-test algorithmic robustness and verify C++ transpilation end-to-end, we construct a parameterized simulator (`src/simulator.py`). 

### Mathematical Formulation
1. **Base Distribution**: Fitted from empirical class parameters ($\mu_{\text{fresh}} = 577.6, \sigma_{\text{fresh}} = 75.0, \mu_{\text{spoiled}} = 1094.3, \sigma_{\text{spoiled}} = 95.8$).
2. **Colored Noise Generation**: Autoregressive AR(1) process capturing temporal sensor noise:
   $$x_t = \phi x_{t-1} + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, \sigma_{\epsilon}^2), \quad \phi = 0.88$$
3. **Sensor Baseline Drift**: Linear long-term baseline drift parameter $\delta_t = \kappa \cdot t$.
4. **Gain Variation**: Sensor-to-sensor sensitivity scale $g \sim \mathcal{N}(1.0, 0.03^2)$.
5. **Cross-Sensitivity Model (Simulated Assumption)**: An empirical model coupling simulated ambient temperature ($T$) and relative humidity ($RH$):
   $$ADC_{\text{observed}} = \left[ ADC_{\text{base}} \cdot \left(1 + \alpha (T - 20) + \beta (RH - 55)\right) \cdot g \right] + x_t + \delta_t$$
   with $\alpha = 0.003/^\circ\text{C}$ and $\beta = 0.002/\%$ RH.

> **Research Transparency Disclaimer**: Every simulated record is tagged with `is_synthetic = 1`, generator metadata, parameters, and random seed. Synthetic datasets are strictly isolated from real experimental results and are used solely to generate sensitivity curves (Accuracy vs. Class Overlap, Noise, and Drift).

---

## 6. Embedded C++ TinyML Transpilation and Verification

Because the hardware feature space is univariate and constrained to a 12-bit ADC integer domain ($x \in \{0, 1, \dots, 4095\}$), complex machine learning runtimes (e.g., TensorFlow Lite Micro) impose unnecessary heap and runtime overhead.

### Zero-Allocation Flash Lookup Architecture
We pre-compute the exact continuous probability $P(\text{SPOILED} \mid x)$ and decision output across all 4,096 discrete ADC values. The model transpiles directly into a static C++ array stored in MCU program flash (`PROGMEM`):
```cpp
static const float HYBRID_PROB_LUT[4096] PROGMEM = { ... };

static inline const char* predictStage(float mq135) {
  int adc = (int)mq135;
  if (adc < 0) adc = 0;
  else if (adc > 4095) adc = 4095;
  return (adc >= 738) ? "LATE" : "EARLY";
}

static inline float predictLateProbability(float mq135) {
  int adc = (int)mq135;
  if (adc < 0) adc = 0;
  else if (adc > 4095) adc = 4095;
  return HYBRID_PROB_LUT[adc];
}
```

### Verification Protocol
1. **Mathematical Parity**: An automated test script (`src/verify_export.py`) compares the C++ header logic against the Python pipeline across all 4,096 discrete integers. Parity is confirmed at **0 discrepancies (100.00% exact match)** with a maximum probability delta of $5.1 \times 10^{-7}$.
2. **Compiler Resource Footprint**: Compiled via `arduino-cli 1.5.1` (GCC Xtensa for `esp32:esp32`):
   - Program Storage (Flash): **296,972 bytes (22.0%)**
   - Dynamic SRAM: **22,212 bytes (6.0%)**
   - Dynamic Heap Allocations: **0 bytes**
   - Latency: Verified via hardware instruction cycles as **$< 1.0\ \mu\text{s}$ per inference** ($O(1)$ memory fetch).
