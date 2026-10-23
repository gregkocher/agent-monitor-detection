# Round-4 paired ΔUS contrasts (n=28 base attacks, 14 tasks; honest n=550)

Joint paired bootstrap (amd.evaluation.paired): honest+attacks resampled together, task-clustered, threshold recalibrated per replicate. US=valid·(1−P(alarm)); invalid→+inf.

| validity | contrast | detector | alpha | realized FPR | ΔUS [95% CI] | p(Δ≤0) |
|---|---|---|---|---|---|---|
| exec | rewrite_control − original | max | 0.01 | 0.0141 | -0.214 [-0.480,+0.032] | 0.968 |
| exec | rewrite_control − original | max | 0.003 | 0.0070 | -0.166 [-0.440,+0.000] | 0.978 |
| exec | rewrite_control − original | multichart | 0.01 | 0.0160 | -0.250 [-0.478,-0.018] | 0.984 |
| exec | rewrite_control − original | multichart | 0.003 | 0.0078 | -0.163 [-0.429,+0.000] | 0.979 |
| exec | rewrite_control − original | cusum1.5 | 0.01 | 0.0136 | -0.214 [-0.458,+0.000] | 0.976 |
| exec | rewrite_control − original | cusum1.5 | 0.003 | 0.0061 | -0.202 [-0.440,+0.029] | 0.966 |
| exec | rewrite_control − original | top3sum | 0.01 | 0.0140 | -0.107 [-0.364,+0.088] | 0.885 |
| exec | rewrite_control − original | top3sum | 0.003 | 0.0071 | -0.155 [-0.407,+0.050] | 0.933 |
| exec | pace_max − original | max | 0.01 | 0.0141 | -0.321 [-0.625,-0.034] | 0.990 |
| exec | pace_max − original | max | 0.003 | 0.0070 | -0.261 [-0.572,-0.006] | 0.985 |
| exec | pace_max − original | multichart | 0.01 | 0.0160 | -0.357 [-0.621,-0.065] | 0.994 |
| exec | pace_max − original | multichart | 0.003 | 0.0078 | -0.254 [-0.553,-0.024] | 0.982 |
| exec | pace_max − original | cusum1.5 | 0.01 | 0.0136 | -0.179 [-0.481,+0.071] | 0.938 |
| exec | pace_max − original | cusum1.5 | 0.003 | 0.0061 | -0.286 [-0.565,+0.000] | 0.979 |
| exec | pace_max − original | top3sum | 0.01 | 0.0140 | -0.214 [-0.500,+0.000] | 0.983 |
| exec | pace_max − original | top3sum | 0.003 | 0.0071 | -0.239 [-0.528,+0.000] | 0.983 |
| exec | pace_max − rewrite_control | max | 0.01 | 0.0141 | -0.107 [-0.357,+0.120] | 0.835 |
| exec | pace_max − rewrite_control | max | 0.003 | 0.0070 | -0.095 [-0.355,+0.182] | 0.778 |
| exec | pace_max − rewrite_control | multichart | 0.01 | 0.0160 | -0.107 [-0.360,+0.130] | 0.819 |
| exec | pace_max − rewrite_control | multichart | 0.003 | 0.0078 | -0.091 [-0.361,+0.188] | 0.761 |
| exec | pace_max − rewrite_control | cusum1.5 | 0.01 | 0.0136 | +0.036 [-0.299,+0.274] | 0.506 |
| exec | pace_max − rewrite_control | cusum1.5 | 0.003 | 0.0061 | -0.084 [-0.360,+0.188] | 0.725 |
| exec | pace_max − rewrite_control | top3sum | 0.01 | 0.0140 | -0.107 [-0.400,+0.143] | 0.843 |
| exec | pace_max − rewrite_control | top3sum | 0.003 | 0.0071 | -0.084 [-0.370,+0.160] | 0.787 |
| judge | rewrite_control − original | max | 0.01 | 0.0141 | -0.304 [-0.500,-0.080] | 0.998 |
| judge | rewrite_control − original | max | 0.003 | 0.0070 | -0.238 [-0.435,-0.077] | 0.999 |
| judge | rewrite_control − original | multichart | 0.01 | 0.0160 | -0.321 [-0.478,-0.107] | 0.998 |
| judge | rewrite_control − original | multichart | 0.003 | 0.0078 | -0.234 [-0.414,-0.084] | 0.999 |
| judge | rewrite_control − original | cusum1.5 | 0.01 | 0.0136 | -0.286 [-0.438,-0.095] | 1.000 |
| judge | rewrite_control − original | cusum1.5 | 0.003 | 0.0061 | -0.261 [-0.399,-0.094] | 1.000 |
| judge | rewrite_control − original | top3sum | 0.01 | 0.0140 | -0.179 [-0.348,+0.040] | 0.956 |
| judge | rewrite_control − original | top3sum | 0.003 | 0.0071 | -0.191 [-0.354,-0.008] | 0.985 |
| judge | pace_max − original | max | 0.01 | 0.0141 | -0.268 [-0.483,+0.000] | 0.977 |
| judge | pace_max − original | max | 0.003 | 0.0070 | -0.190 [-0.414,+0.042] | 0.959 |
| judge | pace_max − original | multichart | 0.01 | 0.0160 | -0.286 [-0.463,-0.010] | 0.982 |
| judge | pace_max − original | multichart | 0.003 | 0.0078 | -0.182 [-0.398,+0.036] | 0.957 |
| judge | pace_max − original | cusum1.5 | 0.01 | 0.0136 | -0.107 [-0.344,+0.115] | 0.899 |
| judge | pace_max − original | cusum1.5 | 0.003 | 0.0061 | -0.238 [-0.402,+0.000] | 0.985 |
| judge | pace_max − original | top3sum | 0.01 | 0.0140 | -0.286 [-0.481,-0.042] | 0.992 |
| judge | pace_max − original | top3sum | 0.003 | 0.0071 | -0.262 [-0.467,-0.051] | 0.993 |
| judge | pace_max − rewrite_control | max | 0.01 | 0.0141 | +0.036 [-0.100,+0.199] | 0.385 |
| judge | pace_max − rewrite_control | max | 0.003 | 0.0070 | +0.048 [-0.110,+0.251] | 0.313 |
| judge | pace_max − rewrite_control | multichart | 0.01 | 0.0160 | +0.036 [-0.108,+0.211] | 0.367 |
| judge | pace_max − rewrite_control | multichart | 0.003 | 0.0078 | +0.052 [-0.107,+0.250] | 0.291 |
| judge | pace_max − rewrite_control | cusum1.5 | 0.01 | 0.0136 | +0.179 [-0.046,+0.333] | 0.083 |
| judge | pace_max − rewrite_control | cusum1.5 | 0.003 | 0.0061 | +0.023 [-0.107,+0.240] | 0.371 |
| judge | pace_max − rewrite_control | top3sum | 0.01 | 0.0140 | -0.107 [-0.357,+0.143] | 0.856 |
| judge | pace_max − rewrite_control | top3sum | 0.003 | 0.0071 | -0.071 [-0.273,+0.124] | 0.830 |
