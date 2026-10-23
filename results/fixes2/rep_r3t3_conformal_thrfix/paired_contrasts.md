# Round-3 paired contrasts in undetected-success (with-output; strict validity; one-shot; n=35 base attacks, 17 tasks; honest n=550)

Joint paired bootstrap (amd.evaluation.paired): honest + attacks resampled together, clustered by task, threshold recalibrated per replicate. 95% CI; p = P(boot ≤ 0).

| contrast | detector | alpha | ΔUS [95% CI] | p(Δ≤0) |
|---|---|---|---|---|
| control/gpt41 − original | max | 0.01 | -0.572 [-0.718,-0.378] | 1.000 |
| control/gpt41 − original | max | 0.003 | -0.476 [-0.684,-0.280] | 1.000 |
| control/gpt41 − original | multichart | 0.01 | -0.543 [-0.703,-0.358] | 1.000 |
| control/gpt41 − original | multichart | 0.003 | -0.473 [-0.667,-0.281] | 1.000 |
| control/gpt41 − original | cusum1.5 | 0.01 | -0.514 [-0.653,-0.286] | 1.000 |
| control/gpt41 − original | cusum1.5 | 0.003 | -0.379 [-0.591,-0.172] | 1.000 |
| control/gpt41 − original | top3sum | 0.01 | -0.486 [-0.675,-0.276] | 1.000 |
| control/gpt41 − original | top3sum | 0.003 | -0.409 [-0.615,-0.219] | 1.000 |
| pace_max/gpt41 − control/gpt41 | max | 0.01 | +0.072 [-0.107,+0.250] | 0.258 |
| pace_max/gpt41 − control/gpt41 | max | 0.003 | +0.038 [-0.112,+0.189] | 0.331 |
| pace_max/gpt41 − control/gpt41 | multichart | 0.01 | +0.029 [-0.132,+0.215] | 0.377 |
| pace_max/gpt41 − control/gpt41 | multichart | 0.003 | +0.026 [-0.116,+0.170] | 0.385 |
| pace_max/gpt41 − control/gpt41 | cusum1.5 | 0.01 | +0.143 [-0.034,+0.244] | 0.071 |
| pace_max/gpt41 − control/gpt41 | cusum1.5 | 0.003 | -0.001 [-0.156,+0.188] | 0.477 |
| pace_max/gpt41 − control/gpt41 | top3sum | 0.01 | +0.014 [-0.148,+0.207] | 0.431 |
| pace_max/gpt41 − control/gpt41 | top3sum | 0.003 | -0.087 [-0.276,+0.132] | 0.766 |
| pace_cusum/gpt41 − control/gpt41 | max | 0.01 | -0.043 [-0.201,+0.061] | 0.829 |
| pace_cusum/gpt41 − control/gpt41 | max | 0.003 | -0.037 [-0.197,+0.083] | 0.761 |
| pace_cusum/gpt41 − control/gpt41 | multichart | 0.01 | -0.086 [-0.247,+0.061] | 0.867 |
| pace_cusum/gpt41 − control/gpt41 | multichart | 0.003 | -0.063 [-0.213,+0.062] | 0.831 |
| pace_cusum/gpt41 − control/gpt41 | cusum1.5 | 0.01 | -0.029 [-0.143,+0.073] | 0.759 |
| pace_cusum/gpt41 − control/gpt41 | cusum1.5 | 0.003 | +0.009 [-0.125,+0.101] | 0.642 |
| pace_cusum/gpt41 − control/gpt41 | top3sum | 0.01 | -0.100 [-0.256,+0.094] | 0.851 |
| pace_cusum/gpt41 − control/gpt41 | top3sum | 0.003 | -0.132 [-0.284,+0.073] | 0.905 |
| pace_multichart/gpt41 − control/gpt41 | max | 0.01 | +0.086 [-0.047,+0.194] | 0.173 |
| pace_multichart/gpt41 − control/gpt41 | max | 0.003 | +0.029 [-0.091,+0.161] | 0.316 |
| pace_multichart/gpt41 − control/gpt41 | multichart | 0.01 | +0.029 [-0.100,+0.167] | 0.359 |
| pace_multichart/gpt41 − control/gpt41 | multichart | 0.003 | -0.003 [-0.111,+0.121] | 0.503 |
| pace_multichart/gpt41 − control/gpt41 | cusum1.5 | 0.01 | +0.029 [-0.107,+0.170] | 0.339 |
| pace_multichart/gpt41 − control/gpt41 | cusum1.5 | 0.003 | +0.047 [-0.086,+0.179] | 0.300 |
| pace_multichart/gpt41 − control/gpt41 | top3sum | 0.01 | +0.000 [-0.153,+0.188] | 0.501 |
| pace_multichart/gpt41 − control/gpt41 | top3sum | 0.003 | -0.067 [-0.188,+0.098] | 0.792 |
| control/gemini − original | max | 0.01 | -0.385 [-0.556,-0.195] | 1.000 |
| control/gemini − original | max | 0.003 | -0.285 [-0.513,-0.089] | 0.999 |
| control/gemini − original | multichart | 0.01 | -0.400 [-0.554,-0.193] | 1.000 |
| control/gemini − original | multichart | 0.003 | -0.276 [-0.485,-0.102] | 1.000 |
| control/gemini − original | cusum1.5 | 0.01 | -0.314 [-0.474,-0.143] | 0.999 |
| control/gemini − original | cusum1.5 | 0.003 | -0.266 [-0.442,-0.081] | 0.998 |
| control/gemini − original | top3sum | 0.01 | -0.272 [-0.415,-0.111] | 1.000 |
| control/gemini − original | top3sum | 0.003 | -0.296 [-0.439,-0.114] | 0.999 |
| pace_max/gemini − control/gemini | max | 0.01 | -0.101 [-0.288,+0.069] | 0.887 |
| pace_max/gemini − control/gemini | max | 0.003 | -0.134 [-0.294,+0.049] | 0.925 |
| pace_max/gemini − control/gemini | multichart | 0.01 | -0.086 [-0.269,+0.072] | 0.871 |
| pace_max/gemini − control/gemini | multichart | 0.003 | -0.140 [-0.294,+0.035] | 0.940 |
| pace_max/gemini − control/gemini | cusum1.5 | 0.01 | -0.029 [-0.208,+0.120] | 0.775 |
| pace_max/gemini − control/gemini | cusum1.5 | 0.003 | -0.153 [-0.308,+0.063] | 0.911 |
| pace_max/gemini − control/gemini | top3sum | 0.01 | -0.157 [-0.293,+0.034] | 0.957 |
| pace_max/gemini − control/gemini | top3sum | 0.003 | -0.133 [-0.300,+0.040] | 0.948 |
| pace_cusum/gemini − control/gemini | max | 0.01 | -0.129 [-0.317,+0.063] | 0.913 |
| pace_cusum/gemini − control/gemini | max | 0.003 | -0.181 [-0.363,+0.024] | 0.959 |
| pace_cusum/gemini − control/gemini | multichart | 0.01 | -0.086 [-0.318,+0.066] | 0.901 |
| pace_cusum/gemini − control/gemini | multichart | 0.003 | -0.184 [-0.366,+0.007] | 0.970 |
| pace_cusum/gemini − control/gemini | cusum1.5 | 0.01 | -0.114 [-0.299,+0.044] | 0.945 |
| pace_cusum/gemini − control/gemini | cusum1.5 | 0.003 | -0.143 [-0.297,+0.036] | 0.950 |
| pace_cusum/gemini − control/gemini | top3sum | 0.01 | -0.143 [-0.321,+0.029] | 0.959 |
| pace_cusum/gemini − control/gemini | top3sum | 0.003 | -0.113 [-0.289,+0.031] | 0.944 |
| pace_multichart/gemini − control/gemini | max | 0.01 | -0.015 [-0.209,+0.128] | 0.722 |
| pace_multichart/gemini − control/gemini | max | 0.003 | -0.124 [-0.257,+0.088] | 0.879 |
| pace_multichart/gemini − control/gemini | multichart | 0.01 | -0.029 [-0.216,+0.133] | 0.700 |
| pace_multichart/gemini − control/gemini | multichart | 0.003 | -0.127 [-0.265,+0.055] | 0.906 |
| pace_multichart/gemini − control/gemini | cusum1.5 | 0.01 | -0.029 [-0.200,+0.118] | 0.736 |
| pace_multichart/gemini − control/gemini | cusum1.5 | 0.003 | -0.124 [-0.266,+0.050] | 0.912 |
| pace_multichart/gemini − control/gemini | top3sum | 0.01 | -0.157 [-0.304,+0.026] | 0.961 |
| pace_multichart/gemini − control/gemini | top3sum | 0.003 | -0.067 [-0.268,+0.052] | 0.919 |
| rewrite_control: gpt-4.1 − gemini | max | 0.01 | -0.187 [-0.339,-0.040] | 0.998 |
| rewrite_control: gpt-4.1 − gemini | max | 0.003 | -0.191 [-0.333,-0.034] | 0.995 |
| rewrite_control: gpt-4.1 − gemini | multichart | 0.01 | -0.143 [-0.302,-0.029] | 0.994 |
| rewrite_control: gpt-4.1 − gemini | multichart | 0.003 | -0.197 [-0.320,-0.036] | 0.995 |
| rewrite_control: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.200 [-0.321,-0.026] | 0.991 |
| rewrite_control: gpt-4.1 − gemini | cusum1.5 | 0.003 | -0.113 [-0.262,+0.062] | 0.914 |
| rewrite_control: gpt-4.1 − gemini | top3sum | 0.01 | -0.214 [-0.361,-0.062] | 0.998 |
| rewrite_control: gpt-4.1 − gemini | top3sum | 0.003 | -0.113 [-0.303,+0.059] | 0.923 |
| pace_max: gpt-4.1 − gemini | max | 0.01 | -0.013 [-0.192,+0.162] | 0.560 |
| pace_max: gpt-4.1 − gemini | max | 0.003 | -0.019 [-0.166,+0.100] | 0.647 |
| pace_max: gpt-4.1 − gemini | multichart | 0.01 | -0.029 [-0.191,+0.125] | 0.681 |
| pace_max: gpt-4.1 − gemini | multichart | 0.003 | -0.031 [-0.162,+0.088] | 0.705 |
| pace_max: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.029 [-0.156,+0.128] | 0.621 |
| pace_max: gpt-4.1 − gemini | cusum1.5 | 0.003 | +0.038 [-0.123,+0.171] | 0.386 |
| pace_max: gpt-4.1 − gemini | top3sum | 0.01 | -0.043 [-0.206,+0.073] | 0.838 |
| pace_max: gpt-4.1 − gemini | top3sum | 0.003 | -0.067 [-0.215,+0.063] | 0.863 |
| pace_cusum: gpt-4.1 − gemini | max | 0.01 | -0.100 [-0.270,+0.034] | 0.950 |
| pace_cusum: gpt-4.1 − gemini | max | 0.003 | -0.047 [-0.250,+0.169] | 0.766 |
| pace_cusum: gpt-4.1 − gemini | multichart | 0.01 | -0.143 [-0.287,+0.042] | 0.937 |
| pace_cusum: gpt-4.1 − gemini | multichart | 0.003 | -0.076 [-0.272,+0.126] | 0.799 |
| pace_cusum: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.114 [-0.243,+0.083] | 0.882 |
| pace_cusum: gpt-4.1 − gemini | cusum1.5 | 0.003 | +0.038 [-0.161,+0.176] | 0.462 |
| pace_cusum: gpt-4.1 − gemini | top3sum | 0.01 | -0.171 [-0.290,-0.032] | 0.996 |
| pace_cusum: gpt-4.1 − gemini | top3sum | 0.003 | -0.132 [-0.267,+0.059] | 0.935 |
| pace_multichart: gpt-4.1 − gemini | max | 0.01 | -0.086 [-0.233,+0.091] | 0.847 |
| pace_multichart: gpt-4.1 − gemini | max | 0.003 | -0.038 [-0.250,+0.129] | 0.716 |
| pace_multichart: gpt-4.1 − gemini | multichart | 0.01 | -0.086 [-0.250,+0.066] | 0.894 |
| pace_multichart: gpt-4.1 − gemini | multichart | 0.003 | -0.073 [-0.257,+0.092] | 0.805 |
| pace_multichart: gpt-4.1 − gemini | cusum1.5 | 0.01 | -0.143 [-0.300,+0.091] | 0.882 |
| pace_multichart: gpt-4.1 − gemini | cusum1.5 | 0.003 | +0.058 [-0.180,+0.226] | 0.340 |
| pace_multichart: gpt-4.1 − gemini | top3sum | 0.01 | -0.057 [-0.242,+0.105] | 0.823 |
| pace_multichart: gpt-4.1 − gemini | top3sum | 0.003 | -0.113 [-0.259,+0.107] | 0.814 |
