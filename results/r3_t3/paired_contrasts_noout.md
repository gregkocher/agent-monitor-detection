# Round-3 paired contrasts in undetected-success (no-output; strict validity; one-shot; n=35 base attacks, 17 tasks; honest n=250)

Joint paired bootstrap (amd.evaluation.paired): honest + attacks resampled together, clustered by task, threshold recalibrated per replicate. 95% CI; p = P(boot ≤ 0).

| contrast | detector | alpha | ΔUS [95% CI] | p(Δ≤0) |
|---|---|---|---|---|
| control/gpt41 − original | max | 0.01 | -0.514 [-0.667,-0.321] | 1.000 |
| control/gpt41 − original | multichart | 0.01 | -0.514 [-0.655,-0.333] | 1.000 |
| control/gpt41 − original | cusum1.5 | 0.01 | -0.314 [-0.605,-0.172] | 1.000 |
| control/gpt41 − original | top3sum | 0.01 | -0.371 [-0.632,-0.214] | 1.000 |
| pace_max/gpt41 − control/gpt41 | max | 0.01 | +0.029 [-0.158,+0.139] | 0.679 |
| pace_max/gpt41 − control/gpt41 | multichart | 0.01 | -0.021 [-0.163,+0.110] | 0.702 |
| pace_max/gpt41 − control/gpt41 | cusum1.5 | 0.01 | -0.029 [-0.192,+0.152] | 0.722 |
| pace_max/gpt41 − control/gpt41 | top3sum | 0.01 | -0.257 [-0.423,+0.077] | 0.904 |
| pace_cusum/gpt41 − control/gpt41 | max | 0.01 | +0.029 [-0.135,+0.121] | 0.570 |
| pace_cusum/gpt41 − control/gpt41 | multichart | 0.01 | +0.007 [-0.119,+0.105] | 0.474 |
| pace_cusum/gpt41 − control/gpt41 | cusum1.5 | 0.01 | -0.114 [-0.220,+0.073] | 0.912 |
| pace_cusum/gpt41 − control/gpt41 | top3sum | 0.01 | -0.229 [-0.359,+0.030] | 0.954 |
| pace_multichart/gpt41 − control/gpt41 | max | 0.01 | +0.086 [-0.135,+0.192] | 0.367 |
| pace_multichart/gpt41 − control/gpt41 | multichart | 0.01 | +0.079 [-0.122,+0.176] | 0.258 |
| pace_multichart/gpt41 − control/gpt41 | cusum1.5 | 0.01 | -0.029 [-0.156,+0.121] | 0.761 |
| pace_multichart/gpt41 − control/gpt41 | top3sum | 0.01 | -0.171 [-0.286,+0.025] | 0.971 |
| control/gemini − original | max | 0.01 | -0.314 [-0.536,-0.179] | 1.000 |
| control/gemini − original | multichart | 0.01 | -0.314 [-0.513,-0.169] | 1.000 |
| control/gemini − original | cusum1.5 | 0.01 | -0.229 [-0.439,-0.062] | 0.997 |
| control/gemini − original | top3sum | 0.01 | -0.314 [-0.500,-0.138] | 0.998 |
| pace_max/gemini − control/gemini | max | 0.01 | -0.143 [-0.293,+0.118] | 0.847 |
| pace_max/gemini − control/gemini | multichart | 0.01 | -0.121 [-0.287,+0.112] | 0.860 |
| pace_max/gemini − control/gemini | cusum1.5 | 0.01 | -0.114 [-0.257,+0.059] | 0.923 |
| pace_max/gemini − control/gemini | top3sum | 0.01 | -0.143 [-0.303,+0.065] | 0.926 |
| pace_cusum/gemini − control/gemini | max | 0.01 | -0.114 [-0.294,+0.121] | 0.815 |
| pace_cusum/gemini − control/gemini | multichart | 0.01 | -0.136 [-0.305,+0.081] | 0.889 |
| pace_cusum/gemini − control/gemini | cusum1.5 | 0.01 | -0.143 [-0.292,+0.047] | 0.949 |
| pace_cusum/gemini − control/gemini | top3sum | 0.01 | -0.086 [-0.256,+0.071] | 0.891 |
| pace_multichart/gemini − control/gemini | max | 0.01 | -0.143 [-0.263,+0.111] | 0.857 |
| pace_multichart/gemini − control/gemini | multichart | 0.01 | -0.143 [-0.254,+0.107] | 0.883 |
| pace_multichart/gemini − control/gemini | cusum1.5 | 0.01 | -0.086 [-0.242,+0.053] | 0.918 |
| pace_multichart/gemini − control/gemini | top3sum | 0.01 | -0.114 [-0.269,+0.057] | 0.931 |
| rewrite_control: gpt-4.1 − gemini | max | 0.01 | -0.200 [-0.308,+0.057] | 0.947 |
| rewrite_control: gpt-4.1 − gemini | multichart | 0.01 | -0.200 [-0.301,+0.034] | 0.959 |
| rewrite_control: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.086 [-0.267,+0.059] | 0.917 |
| rewrite_control: gpt-4.1 − gemini | top3sum | 0.01 | -0.057 [-0.259,+0.111] | 0.875 |
| pace_max: gpt-4.1 − gemini | max | 0.01 | -0.029 [-0.242,+0.118] | 0.829 |
| pace_max: gpt-4.1 − gemini | multichart | 0.01 | -0.100 [-0.257,+0.061] | 0.871 |
| pace_max: gpt-4.1 − gemini | cusum1.5 | 0.01 | +0.000 [-0.177,+0.143] | 0.620 |
| pace_max: gpt-4.1 − gemini | top3sum | 0.01 | -0.171 [-0.323,+0.026] | 0.968 |
| pace_cusum: gpt-4.1 − gemini | max | 0.01 | -0.057 [-0.222,+0.143] | 0.802 |
| pace_cusum: gpt-4.1 − gemini | multichart | 0.01 | -0.057 [-0.195,+0.114] | 0.737 |
| pace_cusum: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.057 [-0.226,+0.150] | 0.765 |
| pace_cusum: gpt-4.1 − gemini | top3sum | 0.01 | -0.200 [-0.313,-0.024] | 0.990 |
| pace_multichart: gpt-4.1 − gemini | max | 0.01 | +0.029 [-0.214,+0.156] | 0.609 |
| pace_multichart: gpt-4.1 − gemini | multichart | 0.01 | +0.021 [-0.212,+0.152] | 0.479 |
| pace_multichart: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.029 [-0.177,+0.125] | 0.747 |
| pace_multichart: gpt-4.1 − gemini | top3sum | 0.01 | -0.114 [-0.279,+0.062] | 0.940 |
