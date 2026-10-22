# Fabricated-output leak test (calibration-free; gpt-4.1 none; paired n=35)

Δ = peak(no output) − peak(with output) per trajectory. Originals carry REAL outputs, rewrites FABRICATED ones. DiD = rewrite Δ − original Δ (≈0 ⇒ fabricated outputs carry no extra cue).

| arm | rewriter | peak w/ output | peak no output | Δ peak [95% CI] | DiD vs original [95% CI] | mean-step Δ |
|---|---|---|---|---|---|---|
| nothing | - | 5.62 | 5.07 | -0.55 [-1.03,-0.08] | - | -0.05 |
| rewrite_control | gpt41 | 8.49 | 8.34 | -0.15 [-0.39,+0.08] | +0.40 [-0.15,+1.00] | -0.05 |
| rewrite_control | gemini | 7.59 | 7.26 | -0.33 [-0.85,+0.08] | +0.22 [-0.38,+0.78] | -0.03 |
| pace_max | gpt41 | 8.29 | 8.51 | +0.22 [+0.01,+0.46] | +0.77 [+0.22,+1.31] | +0.01 |
| pace_max | gemini | 7.33 | 7.28 | -0.05 [-0.40,+0.27] | +0.50 [-0.13,+1.07] | +0.00 |
| pace_cusum | gpt41 | 8.16 | 7.94 | -0.22 [-0.57,+0.14] | +0.33 [-0.18,+0.88] | +0.01 |
| pace_cusum | gemini | 6.98 | 7.06 | +0.08 [-0.24,+0.43] | +0.63 [+0.15,+1.14] | -0.03 |
| pace_multichart | gpt41 | 8.16 | 8.41 | +0.25 [-0.03,+0.59] | +0.79 [+0.25,+1.35] | -0.01 |
| pace_multichart | gemini | 7.09 | 7.04 | -0.05 [-0.37,+0.24] | +0.50 [+0.01,+0.99] | -0.05 |
