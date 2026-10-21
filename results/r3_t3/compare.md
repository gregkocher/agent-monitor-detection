# Round 3B: rewriter != monitor (withoutput; monitor gpt-4.1 none; validity=strict; paired n=35)

One-shot vs one-shot vs originals, paired on identical base attacks. CIs are a paired bootstrap that resamples base attacks and honest runs and recalibrates the randomized threshold on each replicate (includes calibration noise).

## Realized FPR on a held-out honest half (nominal vs achieved)
| detector | alpha | realized FPR |
|---|---|---|
| max | 0.01 | 0.0145 |
| max | 0.003 | 0.0073 |
| cusum1.5 | 0.01 | 0.0291 |
| cusum1.5 | 0.003 | 0.0000 |
| multichart | 0.01 | 0.0315 |
| multichart | 0.003 | 0.0222 |
| top3sum | 0.01 | 0.0036 |
| top3sum | 0.003 | 0.0036 |

## Undetected-success (valid x (1-P alarm)); paired, recalibrated bootstrap


**alpha = 0.01**
| arm | rewriter | max | cusum1.5 | multichart | top3sum |
|---|---|---|---|---|---|
| nothing | - | 0.80 [0.66,0.91] | 0.80 [0.66,0.97] | 0.86 [0.69,0.94] | 0.83 [0.69,0.94] |
| rewrite_control | gpt-4.1 | 0.20 [0.09,0.43] | 0.29 [0.14,0.60] | 0.31 [0.14,0.49] | 0.34 [0.14,0.51] |
| pace_max | gpt-4.1 | 0.31 [0.17,0.49] | 0.43 [0.26,0.66] | 0.34 [0.20,0.52] | 0.34 [0.23,0.54] |
| pace_cusum | gpt-4.1 | 0.17 [0.06,0.37] | 0.26 [0.11,0.57] | 0.23 [0.09,0.41] | 0.23 [0.11,0.43] |
| pace_multichart | gpt-4.1 | 0.29 [0.14,0.51] | 0.31 [0.20,0.66] | 0.34 [0.17,0.52] | 0.34 [0.17,0.51] |
| rewrite_control | gemini | 0.43 [0.26,0.63] | 0.49 [0.31,0.71] | 0.46 [0.29,0.64] | 0.54 [0.36,0.71] |
| pace_max | gemini | 0.29 [0.14,0.51] | 0.46 [0.29,0.67] | 0.37 [0.18,0.54] | 0.40 [0.26,0.57] |
| pace_cusum | gemini | 0.29 [0.17,0.49] | 0.37 [0.20,0.60] | 0.37 [0.17,0.53] | 0.40 [0.23,0.60] |
| pace_multichart | gemini | 0.40 [0.23,0.57] | 0.46 [0.31,0.69] | 0.43 [0.26,0.60] | 0.40 [0.26,0.60] |

_Paired contrasts (alpha=0.01):_

- rewrite_control/gpt41 − original @max: -0.561 [-0.714,-0.400]
- pace_max/gpt41 − original @max: -0.479 [-0.657,-0.286]
- pace_multichart/gpt41 − original @multichart: -0.496 [-0.657,-0.309]
- pace_max/gpt41 − control/gpt41 @max (strategy): +0.082 [-0.101,+0.244]
- pace_multichart/gpt41 − control/gpt41 @multichart (strategy): +0.042 [-0.097,+0.200]
- rewrite_control/gemini − original @max: -0.369 [-0.558,-0.171]
- pace_max/gemini − original @max: -0.483 [-0.672,-0.286]
- pace_multichart/gemini − original @multichart: -0.410 [-0.621,-0.198]
- pace_max/gemini − control/gemini @max (strategy): -0.114 [-0.257,+0.057]
- pace_multichart/gemini − control/gemini @multichart (strategy): -0.040 [-0.257,+0.171]

_Cross-rewriter (gpt-4.1 − gemini, same arm; alpha=0.01):_

- rewrite_control @max: -0.192 [-0.371,-0.057]
- rewrite_control @multichart: -0.169 [-0.343,-0.012]
- pace_max @max: +0.004 [-0.171,+0.143]
- pace_max @multichart: -0.021 [-0.171,+0.116]
- pace_cusum @max: -0.116 [-0.286,+0.057]
- pace_cusum @multichart: -0.122 [-0.286,+0.059]
- pace_multichart @max: -0.071 [-0.257,+0.086]
- pace_multichart @multichart: -0.087 [-0.257,+0.086]

**alpha = 0.003**
| arm | rewriter | max | cusum1.5 | multichart | top3sum |
|---|---|---|---|---|---|
| nothing | - | 0.86 [0.74,0.94] | 0.97 [0.80,1.00] | 0.86 [0.73,0.94] | 0.89 [0.74,0.97] |
| rewrite_control | gpt-4.1 | 0.37 [0.16,0.53] | 0.54 [0.29,0.77] | 0.38 [0.16,0.51] | 0.46 [0.23,0.70] |
| pace_max | gpt-4.1 | 0.40 [0.23,0.57] | 0.57 [0.37,0.74] | 0.39 [0.22,0.55] | 0.40 [0.23,0.57] |
| pace_cusum | gpt-4.1 | 0.31 [0.11,0.51] | 0.57 [0.29,0.77] | 0.28 [0.11,0.43] | 0.29 [0.14,0.60] |
| pace_multichart | gpt-4.1 | 0.40 [0.23,0.57] | 0.60 [0.34,0.80] | 0.36 [0.20,0.51] | 0.40 [0.20,0.60] |
| rewrite_control | gemini | 0.54 [0.31,0.74] | 0.69 [0.43,0.84] | 0.56 [0.34,0.70] | 0.60 [0.40,0.77] |
| pace_max | gemini | 0.43 [0.23,0.60] | 0.54 [0.34,0.71] | 0.43 [0.24,0.59] | 0.46 [0.29,0.63] |
| pace_cusum | gemini | 0.37 [0.20,0.57] | 0.54 [0.31,0.71] | 0.38 [0.22,0.55] | 0.46 [0.29,0.66] |
| pace_multichart | gemini | 0.43 [0.26,0.60] | 0.57 [0.36,0.71] | 0.44 [0.27,0.60] | 0.54 [0.31,0.69] |

_Paired contrasts (alpha=0.003):_

- rewrite_control/gpt41 − original @max: -0.509 [-0.686,-0.343]
- pace_max/gpt41 − original @max: -0.468 [-0.657,-0.257]
- pace_multichart/gpt41 − original @multichart: -0.499 [-0.649,-0.345]
- pace_max/gpt41 − control/gpt41 @max (strategy): +0.040 [-0.114,+0.200]
- pace_multichart/gpt41 − control/gpt41 @multichart (strategy): +0.013 [-0.114,+0.143]
- rewrite_control/gemini − original @max: -0.335 [-0.543,-0.086]
- pace_max/gemini − original @max: -0.451 [-0.629,-0.214]
- pace_multichart/gemini − original @multichart: -0.423 [-0.626,-0.200]
- pace_max/gemini − control/gemini @max (strategy): -0.115 [-0.286,+0.057]
- pace_multichart/gemini − control/gemini @multichart (strategy): -0.081 [-0.288,+0.144]

_Cross-rewriter (gpt-4.1 − gemini, same arm; alpha=0.003):_

- rewrite_control @max: -0.173 [-0.343,+0.000]
- rewrite_control @multichart: -0.170 [-0.341,-0.008]
- pace_max @max: -0.018 [-0.143,+0.114]
- pace_max @multichart: -0.029 [-0.160,+0.098]
- pace_cusum @max: -0.080 [-0.257,+0.114]
- pace_cusum @multichart: -0.106 [-0.272,+0.062]
- pace_multichart @max: -0.043 [-0.244,+0.143]
- pace_multichart @multichart: -0.076 [-0.260,+0.104]

## Peak suspicion, validity, length by rewriter (paired n)

| arm | rewriter | peak(mean) | judge-valid | strict-valid | mean literal-pres | length ratio |
|---|---|---|---|---|---|---|
| nothing | - | 5.62 | 1.00 | 1.00 | 1.00 | 1.00 |
| rewrite_control | gpt-4.1 | 8.49 | 0.94 | 0.77 | 0.91 | 1.17 |
| rewrite_control | gemini | 7.59 | 0.91 | 0.74 | 0.90 | 1.20 |
| pace_max | gpt-4.1 | 8.29 | 0.97 | 0.77 | 0.90 | 1.15 |
| pace_max | gemini | 7.33 | 0.74 | 0.57 | 0.90 | 1.12 |
| pace_cusum | gpt-4.1 | 8.16 | 0.94 | 0.74 | 0.87 | 1.16 |
| pace_cusum | gemini | 6.98 | 0.80 | 0.63 | 0.90 | 1.14 |
| pace_multichart | gpt-4.1 | 8.16 | 0.97 | 0.77 | 0.90 | 1.18 |
| pace_multichart | gemini | 7.09 | 0.77 | 0.60 | 0.90 | 1.12 |
