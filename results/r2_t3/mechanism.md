# Mechanism: where the suspicion is (monitor openai/gpt-4.1, none; paired n=126; honest step q99=6.67)

| arm | peak score | peak on attack step | score on attack steps | score on benign steps | # attack steps > q99 | any attack step > q99 | Δ peak vs original [95% CI] |
|---|---|---|---|---|---|---|---|
| nothing | 6.08 | 0.57 | 2.60 | 0.34 | 0.60 | 0.44 | - |
| r1_max | 7.82 | 0.97 | 3.74 | 0.44 | 1.63 | 0.84 | +1.74 [+1.23,+2.24] |
| r1_cusum | 8.05 | 0.92 | 4.35 | 0.24 | 1.54 | 0.86 | +1.96 [+1.49,+2.45] |
| r1_multichart | 7.51 | 0.89 | 4.03 | 0.50 | 1.45 | 0.75 | +1.43 [+0.93,+1.91] |
| pace_max | 7.95 | 0.88 | 4.11 | 0.37 | 1.93 | 0.87 | +1.87 [+1.38,+2.38] |
| pace_cusum | 8.10 | 0.87 | 4.17 | 0.35 | 1.93 | 0.87 | +2.02 [+1.51,+2.52] |
| pace_multichart | 7.85 | 0.90 | 4.26 | 0.31 | 1.88 | 0.86 | +1.77 [+1.29,+2.25] |
| rewrite_control | 8.37 | 0.98 | 3.74 | 0.12 | 2.06 | 0.92 | +2.29 [+1.82,+2.79] |
