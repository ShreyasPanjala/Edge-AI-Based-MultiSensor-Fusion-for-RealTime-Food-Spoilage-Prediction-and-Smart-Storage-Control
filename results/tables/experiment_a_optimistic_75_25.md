| Model | Accuracy (%) | Precision | Recall | F1-Score | TN | FP | FN | TP | Evaluation Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single-Threshold | 99.97 | 0.9997 | 0.9997 | 0.9997 | 10014 | 0 | 6 | 7258 | Optimistic random split (leaks temporal autocorrelation) |
| Decision Tree | 100.0 | 1.0 | 1.0 | 1.0 | 10014 | 0 | 0 | 7264 | Optimistic random split (leaks temporal autocorrelation) |
| Logistic Regression | 99.99 | 0.9999 | 0.9999 | 0.9999 | 10014 | 0 | 1 | 7263 | Optimistic random split (leaks temporal autocorrelation) |
| Gaussian NB | 99.61 | 0.9961 | 0.9961 | 0.9961 | 10014 | 0 | 68 | 7196 | Optimistic random split (leaks temporal autocorrelation) |
| Random Forest | 100.0 | 1.0 | 1.0 | 1.0 | 10014 | 0 | 0 | 7264 | Optimistic random split (leaks temporal autocorrelation) |
| Soft-Voting Hybrid | 99.99 | 0.9999 | 0.9999 | 0.9999 | 10014 | 0 | 1 | 7263 | Optimistic random split (leaks temporal autocorrelation) |
| Stacking Hybrid | 99.99 | 0.9999 | 0.9999 | 0.9999 | 10014 | 0 | 1 | 7263 | Optimistic random split (leaks temporal autocorrelation) |