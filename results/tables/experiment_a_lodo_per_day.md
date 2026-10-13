| Model | Held-Out Day | True State | Samples | Accuracy (%) | Precision | Recall | F1-Score | TN | FP | FN | TP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single-Threshold | D1 | FRESH | 27707 | 100.0 | 1.0 | 1.0 | 1.0 | 27707 | 0 | 0 | 0 |
| Single-Threshold | D2 | FRESH | 12347 | 100.0 | 1.0 | 1.0 | 1.0 | 12347 | 0 | 0 | 0 |
| Single-Threshold | D4 | SPOILED | 14369 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14369 |
| Single-Threshold | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |
| Decision Tree | D1 | FRESH | 27707 | 100.0 | 1.0 | 1.0 | 1.0 | 27707 | 0 | 0 | 0 |
| Decision Tree | D2 | FRESH | 12347 | 14.08 | 1.0 | 0.1408 | 0.2469 | 1739 | 10608 | 0 | 0 |
| Decision Tree | D4 | SPOILED | 14369 | 90.9 | 1.0 | 0.909 | 0.9524 | 0 | 0 | 1307 | 13062 |
| Decision Tree | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |
| Logistic Regression | D1 | FRESH | 27707 | 100.0 | 1.0 | 1.0 | 1.0 | 27707 | 0 | 0 | 0 |
| Logistic Regression | D2 | FRESH | 12347 | 92.48 | 1.0 | 0.9248 | 0.961 | 11419 | 928 | 0 | 0 |
| Logistic Regression | D4 | SPOILED | 14369 | 86.32 | 1.0 | 0.8632 | 0.9266 | 0 | 0 | 1965 | 12404 |
| Logistic Regression | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |
| Gaussian NB | D1 | FRESH | 27707 | 91.56 | 1.0 | 0.9156 | 0.9559 | 25369 | 2338 | 0 | 0 |
| Gaussian NB | D2 | FRESH | 12347 | 4.23 | 1.0 | 0.0423 | 0.0811 | 522 | 11825 | 0 | 0 |
| Gaussian NB | D4 | SPOILED | 14369 | 83.94 | 1.0 | 0.8394 | 0.9127 | 0 | 0 | 2308 | 12061 |
| Gaussian NB | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |
| Random Forest | D1 | FRESH | 27707 | 100.0 | 1.0 | 1.0 | 1.0 | 27707 | 0 | 0 | 0 |
| Random Forest | D2 | FRESH | 12347 | 14.08 | 1.0 | 0.1408 | 0.2469 | 1739 | 10608 | 0 | 0 |
| Random Forest | D4 | SPOILED | 14369 | 90.9 | 1.0 | 0.909 | 0.9524 | 0 | 0 | 1307 | 13062 |
| Random Forest | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |
| Soft-Voting Hybrid | D1 | FRESH | 27707 | 100.0 | 1.0 | 1.0 | 1.0 | 27707 | 0 | 0 | 0 |
| Soft-Voting Hybrid | D2 | FRESH | 12347 | 14.08 | 1.0 | 0.1408 | 0.2469 | 1739 | 10608 | 0 | 0 |
| Soft-Voting Hybrid | D4 | SPOILED | 14369 | 89.55 | 1.0 | 0.8955 | 0.9449 | 0 | 0 | 1502 | 12867 |
| Soft-Voting Hybrid | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |
| Stacking Hybrid | D1 | FRESH | 27707 | 100.0 | 1.0 | 1.0 | 1.0 | 27707 | 0 | 0 | 0 |
| Stacking Hybrid | D2 | FRESH | 12347 | 14.08 | 1.0 | 0.1408 | 0.2469 | 1739 | 10608 | 0 | 0 |
| Stacking Hybrid | D4 | SPOILED | 14369 | 89.16 | 1.0 | 0.8916 | 0.9427 | 0 | 0 | 1557 | 12812 |
| Stacking Hybrid | D5 | SPOILED | 14687 | 100.0 | 1.0 | 1.0 | 1.0 | 0 | 0 | 0 | 14687 |