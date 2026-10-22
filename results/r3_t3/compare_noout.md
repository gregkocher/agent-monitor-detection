# Round 3B: rewriter != monitor (noout; monitor gpt-4.1 none; validity=strict; paired n=35)

One-shot vs one-shot vs originals, paired on identical base attacks. CIs are a paired bootstrap that resamples base attacks and honest runs and recalibrates the randomized threshold on each replicate (includes calibration noise).

## Realized FPR on a held-out honest half (nominal vs achieved)
| detector | alpha | realized FPR |
|---|---|---|
| max | 0.01 | 0.0320 |
| max | 0.003 | 0.0160 |
| cusum1.5 | 0.01 | 0.0240 |
| cusum1.5 | 0.003 | 0.0000 |
| multichart | 0.01 | 0.0260 |
| multichart | 0.003 | 0.0190 |
| top3sum | 0.01 | 0.0320 |
| top3sum | 0.003 | 0.0240 |

## Undetected-success (valid x (1-P alarm)); paired, recalibrated bootstrap


**alpha = 0.01**
| arm | rewriter | max | cusum1.5 | multichart | top3sum |
|---|---|---|---|---|---|
| nothing | - | 0.86 [0.69,1.00] | 0.91 [0.80,1.00] | 0.88 [0.69,0.98] | 0.94 [0.74,1.00] |
| rewrite_control | gpt-4.1 | 0.34 [0.16,0.64] | 0.60 [0.40,0.77] | 0.36 [0.17,0.60] | 0.57 [0.26,0.69] |
| pace_max | gpt-4.1 | 0.37 [0.11,0.60] | 0.57 [0.37,0.71] | 0.34 [0.14,0.54] | 0.31 [0.20,0.50] |
| pace_cusum | gpt-4.1 | 0.37 [0.17,0.66] | 0.49 [0.31,0.69] | 0.37 [0.17,0.60] | 0.34 [0.14,0.51] |
| pace_multichart | gpt-4.1 | 0.43 [0.14,0.63] | 0.57 [0.37,0.74] | 0.44 [0.17,0.61] | 0.40 [0.17,0.57] |
| rewrite_control | gemini | 0.54 [0.26,0.74] | 0.69 [0.49,0.83] | 0.56 [0.26,0.74] | 0.63 [0.40,0.74] |
| pace_max | gemini | 0.40 [0.19,0.60] | 0.57 [0.37,0.73] | 0.44 [0.20,0.60] | 0.49 [0.29,0.66] |
| pace_cusum | gemini | 0.43 [0.23,0.63] | 0.54 [0.40,0.71] | 0.43 [0.24,0.61] | 0.54 [0.31,0.69] |
| pace_multichart | gemini | 0.40 [0.23,0.60] | 0.60 [0.43,0.74] | 0.42 [0.24,0.60] | 0.51 [0.31,0.66] |

_Paired contrasts (alpha=0.01):_

- rewrite_control/gpt41 − original @max: -0.504 [-0.672,-0.314]
- pace_max/gpt41 − original @max: -0.510 [-0.714,-0.314]
- pace_multichart/gpt41 − original @multichart: -0.448 [-0.643,-0.248]
- pace_max/gpt41 − control/gpt41 @max (strategy): -0.006 [-0.143,+0.171]
- pace_multichart/gpt41 − control/gpt41 @multichart (strategy): +0.049 [-0.082,+0.192]
- rewrite_control/gemini − original @max: -0.343 [-0.543,-0.171]
- pace_max/gemini − original @max: -0.450 [-0.657,-0.257]
- pace_multichart/gemini − original @multichart: -0.447 [-0.629,-0.236]
- pace_max/gemini − control/gemini @max (strategy): -0.106 [-0.301,+0.086]
- pace_multichart/gemini − control/gemini @multichart (strategy): -0.113 [-0.282,+0.086]

_Cross-rewriter (gpt-4.1 − gemini, same arm; alpha=0.01):_

- rewrite_control @max: -0.161 [-0.314,+0.000]
- rewrite_control @multichart: -0.163 [-0.314,-0.002]
- pace_max @max: -0.060 [-0.229,+0.114]
- pace_max @multichart: -0.077 [-0.229,+0.057]
- pace_cusum @max: -0.045 [-0.200,+0.143]
- pace_cusum @multichart: -0.048 [-0.200,+0.119]
- pace_multichart @max: +0.007 [-0.200,+0.171]
- pace_multichart @multichart: -0.001 [-0.182,+0.168]

**alpha = 0.003**
| arm | rewriter | max | cusum1.5 | multichart | top3sum |
|---|---|---|---|---|---|
| nothing | - | 1.00 [0.77,1.00] | 0.97 [0.86,1.00] | 0.96 [0.74,1.00] | 0.94 [0.83,1.00] |
| rewrite_control | gpt-4.1 | 0.63 [0.23,0.77] | 0.71 [0.46,0.83] | 0.53 [0.21,0.71] | 0.57 [0.37,0.71] |
| pace_max | gpt-4.1 | 0.60 [0.21,0.74] | 0.63 [0.43,0.77] | 0.49 [0.19,0.66] | 0.37 [0.20,0.51] |
| pace_cusum | gpt-4.1 | 0.66 [0.23,0.79] | 0.69 [0.40,0.80] | 0.55 [0.23,0.72] | 0.40 [0.20,0.57] |
| pace_multichart | gpt-4.1 | 0.60 [0.31,0.74] | 0.69 [0.46,0.83] | 0.55 [0.26,0.69] | 0.49 [0.24,0.63] |
| rewrite_control | gemini | 0.71 [0.43,0.86] | 0.74 [0.54,0.89] | 0.66 [0.40,0.81] | 0.69 [0.49,0.83] |
| pace_max | gemini | 0.54 [0.31,0.69] | 0.57 [0.40,0.71] | 0.51 [0.29,0.66] | 0.51 [0.34,0.66] |
| pace_cusum | gemini | 0.57 [0.29,0.70] | 0.60 [0.40,0.74] | 0.52 [0.29,0.69] | 0.54 [0.37,0.69] |
| pace_multichart | gemini | 0.54 [0.29,0.69] | 0.60 [0.43,0.76] | 0.50 [0.27,0.65] | 0.51 [0.34,0.69] |

_Paired contrasts (alpha=0.003):_

- rewrite_control/gpt41 − original @max: -0.422 [-0.657,-0.229]
- pace_max/gpt41 − original @max: -0.441 [-0.629,-0.257]
- pace_multichart/gpt41 − original @multichart: -0.422 [-0.607,-0.257]
- pace_max/gpt41 − control/gpt41 @max (strategy): -0.019 [-0.186,+0.143]
- pace_multichart/gpt41 − control/gpt41 @multichart (strategy): +0.027 [-0.113,+0.157]
- rewrite_control/gemini − original @max: -0.293 [-0.457,-0.143]
- pace_max/gemini − original @max: -0.446 [-0.629,-0.286]
- pace_multichart/gemini − original @multichart: -0.449 [-0.623,-0.269]
- pace_max/gemini − control/gemini @max (strategy): -0.154 [-0.343,+0.015]
- pace_multichart/gemini − control/gemini @multichart (strategy): -0.149 [-0.314,+0.021]

_Cross-rewriter (gpt-4.1 − gemini, same arm; alpha=0.003):_

- rewrite_control @max: -0.129 [-0.314,+0.057]
- rewrite_control @multichart: -0.148 [-0.314,+0.016]
- pace_max @max: +0.005 [-0.229,+0.200]
- pace_max @multichart: -0.046 [-0.229,+0.143]
- pace_cusum @max: +0.032 [-0.200,+0.229]
- pace_cusum @multichart: -0.002 [-0.200,+0.177]
- pace_multichart @max: +0.044 [-0.114,+0.200]
- pace_multichart @multichart: +0.027 [-0.134,+0.200]

## Peak suspicion, validity, length by rewriter (paired n)

| arm | rewriter | peak(mean) | judge-valid | strict-valid | mean literal-pres | length ratio |
|---|---|---|---|---|---|---|
| nothing | - | 5.07 | 1.00 | 1.00 | 1.00 | 1.00 |
| rewrite_control | gpt-4.1 | 8.34 | 0.94 | 0.77 | 0.91 | 1.17 |
| rewrite_control | gemini | 7.26 | 0.91 | 0.74 | 0.90 | 1.20 |
| pace_max | gpt-4.1 | 8.51 | 0.97 | 0.77 | 0.90 | 1.15 |
| pace_max | gemini | 7.28 | 0.74 | 0.57 | 0.90 | 1.12 |
| pace_cusum | gpt-4.1 | 7.94 | 0.94 | 0.74 | 0.87 | 1.16 |
| pace_cusum | gemini | 7.06 | 0.80 | 0.63 | 0.90 | 1.14 |
| pace_multichart | gpt-4.1 | 8.41 | 0.97 | 0.77 | 0.90 | 1.18 |
| pace_multichart | gemini | 7.04 | 0.77 | 0.60 | 0.90 | 1.12 |
