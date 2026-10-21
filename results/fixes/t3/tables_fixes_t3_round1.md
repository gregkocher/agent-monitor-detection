# T3 round 1 — audit-corrected tables (monitor gpt-4.1-mini, full and none)

Point estimates reproduce `results/t3/cross_table.csv` (max |diff| 1.1e-16). Joint 95% bootstrap CIs (base attacks + Honest-550, detector refit per replicate, 2000 replicates). Validity bounds as in the round-2 tables (judge / strict / strict-rel). Paired n = 126. Round 1 has NO rewrite-only control under gpt-4.1-mini, so the aware-minus-original difference mixes the detector-aware strategy with the effect of LLM rewriting itself (M3).

## Aware arm − original (nothing), alpha = 0.01

| mode | variant | comparison | detector | judge | strict | strict-rel |
|---|---|---|---|---|---|---|
| full | adaptive | max-aware − original | max | -0.167 [-0.262, -0.095] | -0.341 [-0.437, -0.246] | -0.214 [-0.310, -0.135] |
| full | adaptive | max-aware − original | multichart | -0.357 [-0.471, -0.272] | -0.500 [-0.615, -0.413] | -0.389 [-0.503, -0.310] |
| full | adaptive | cusum-aware − original | max | -0.222 [-0.310, -0.135] | -0.389 [-0.484, -0.294] | -0.262 [-0.357, -0.175] |
| full | adaptive | cusum-aware − original | multichart | -0.270 [-0.359, -0.188] | -0.429 [-0.525, -0.333] | -0.310 [-0.404, -0.223] |
| full | adaptive | multichart-aware − original | max | -0.127 [-0.214, -0.048] | -0.325 [-0.421, -0.230] | -0.198 [-0.286, -0.119] |
| full | adaptive | multichart-aware − original | multichart | -0.173 [-0.284, -0.095] | -0.372 [-0.480, -0.283] | -0.245 [-0.351, -0.167] |
| full | _r0 | max-aware − original | max | -0.325 [-0.429, -0.246] | -0.492 [-0.587, -0.405] | -0.373 [-0.468, -0.286] |
| full | _r0 | max-aware − original | multichart | -0.478 [-0.579, -0.387] | -0.620 [-0.714, -0.529] | -0.509 [-0.611, -0.413] |
| full | _r0 | cusum-aware − original | max | -0.262 [-0.349, -0.175] | -0.429 [-0.524, -0.333] | -0.302 [-0.389, -0.214] |
| full | _r0 | cusum-aware − original | multichart | -0.310 [-0.405, -0.227] | -0.460 [-0.556, -0.366] | -0.349 [-0.445, -0.260] |
| full | _r0 | multichart-aware − original | max | -0.278 [-0.373, -0.183] | -0.460 [-0.556, -0.365] | -0.333 [-0.429, -0.238] |
| full | _r0 | multichart-aware − original | multichart | -0.340 [-0.448, -0.250] | -0.522 [-0.629, -0.429] | -0.396 [-0.500, -0.305] |
| none | adaptive | max-aware − original | max | -0.151 [-0.246, -0.048] | -0.317 [-0.421, -0.198] | -0.190 [-0.294, -0.087] |
| none | adaptive | max-aware − original | multichart | -0.345 [-0.480, -0.273] | -0.464 [-0.603, -0.389] | -0.369 [-0.505, -0.294] |
| none | adaptive | cusum-aware − original | max | -0.206 [-0.294, -0.103] | -0.373 [-0.468, -0.262] | -0.246 [-0.333, -0.143] |
| none | adaptive | cusum-aware − original | multichart | -0.200 [-0.294, -0.117] | -0.358 [-0.460, -0.266] | -0.239 [-0.340, -0.154] |
| none | adaptive | multichart-aware − original | max | -0.119 [-0.214, -0.040] | -0.317 [-0.421, -0.222] | -0.190 [-0.286, -0.111] |
| none | adaptive | multichart-aware − original | multichart | -0.287 [-0.365, -0.175] | -0.454 [-0.538, -0.337] | -0.343 [-0.421, -0.230] |
| none | _r0 | max-aware − original | max | -0.183 [-0.286, -0.095] | -0.341 [-0.452, -0.238] | -0.222 [-0.333, -0.127] |
| none | _r0 | max-aware − original | multichart | -0.397 [-0.524, -0.294] | -0.532 [-0.645, -0.429] | -0.429 [-0.557, -0.325] |
| none | _r0 | cusum-aware − original | max | -0.278 [-0.341, -0.159] | -0.444 [-0.524, -0.302] | -0.317 [-0.389, -0.190] |
| none | _r0 | cusum-aware − original | multichart | -0.257 [-0.356, -0.183] | -0.415 [-0.516, -0.331] | -0.296 [-0.397, -0.216] |
| none | _r0 | multichart-aware − original | max | -0.206 [-0.286, -0.103] | -0.381 [-0.476, -0.270] | -0.254 [-0.341, -0.151] |
| none | _r0 | multichart-aware − original | multichart | -0.366 [-0.454, -0.248] | -0.525 [-0.613, -0.393] | -0.414 [-0.500, -0.288] |

## Levels (alpha = 0.01): judge [joint CI] / strict [joint CI]

| mode | variant | arm | max | cusum | eprocess | multichart |
|---|---|---|---|---|---|---|
| full | adaptive | nothing | 0.857 [0.794, 0.913] / 0.857 [0.794, 0.913] | 0.960 [0.913, 0.992] / 0.960 [0.913, 0.992] | 0.921 [0.865, 0.968] / 0.921 [0.865, 0.968] | 0.851 [0.770, 0.905] / 0.851 [0.770, 0.905] |
| full | adaptive | max | 0.690 [0.595, 0.770] / 0.516 [0.421, 0.603] | 0.738 [0.603, 0.873] / 0.563 [0.437, 0.706] | 0.468 [0.373, 0.571] / 0.325 [0.238, 0.421] | 0.493 [0.373, 0.563] / 0.351 [0.242, 0.413] |
| full | adaptive | cusum | 0.635 [0.540, 0.722] / 0.468 [0.381, 0.563] | 0.857 [0.754, 0.937] / 0.698 [0.587, 0.778] | 0.698 [0.619, 0.794] / 0.548 [0.460, 0.643] | 0.581 [0.477, 0.663] / 0.422 [0.326, 0.506] |
| full | adaptive | multichart | 0.730 [0.643, 0.802] / 0.532 [0.444, 0.611] | 0.810 [0.714, 0.921] / 0.611 [0.508, 0.738] | 0.659 [0.563, 0.770] / 0.468 [0.381, 0.579] | 0.677 [0.554, 0.745] / 0.479 [0.365, 0.551] |
| full | _r0 | nothing | 0.857 [0.794, 0.921] / 0.857 [0.794, 0.921] | 0.960 [0.913, 0.992] / 0.960 [0.913, 0.992] | 0.921 [0.865, 0.968] / 0.921 [0.865, 0.968] | 0.851 [0.774, 0.906] / 0.851 [0.774, 0.906] |
| full | _r0 | max | 0.532 [0.429, 0.619] / 0.365 [0.270, 0.452] | 0.611 [0.460, 0.754] / 0.452 [0.317, 0.595] | 0.373 [0.278, 0.468] / 0.230 [0.143, 0.310] | 0.373 [0.274, 0.452] / 0.230 [0.145, 0.298] |
| full | _r0 | cusum | 0.595 [0.508, 0.690] / 0.429 [0.349, 0.524] | 0.762 [0.667, 0.873] / 0.611 [0.508, 0.714] | 0.643 [0.556, 0.730] / 0.500 [0.413, 0.595] | 0.541 [0.442, 0.620] / 0.390 [0.294, 0.470] |
| full | _r0 | multichart | 0.579 [0.492, 0.667] / 0.397 [0.317, 0.484] | 0.730 [0.611, 0.857] / 0.540 [0.421, 0.683] | 0.532 [0.429, 0.643] / 0.357 [0.262, 0.460] | 0.511 [0.397, 0.595] / 0.328 [0.226, 0.405] |
| none | adaptive | nothing | 0.857 [0.738, 0.960] / 0.857 [0.738, 0.960] | 0.937 [0.881, 0.976] / 0.937 [0.881, 0.976] | 0.905 [0.849, 0.952] / 0.905 [0.849, 0.952] | 0.873 [0.745, 0.921] / 0.873 [0.745, 0.921] |
| none | adaptive | max | 0.706 [0.548, 0.881] / 0.540 [0.381, 0.714] | 0.810 [0.619, 0.905] / 0.659 [0.484, 0.754] | 0.500 [0.397, 0.627] / 0.373 [0.286, 0.500] | 0.528 [0.345, 0.591] / 0.409 [0.234, 0.474] |
| none | adaptive | cusum | 0.651 [0.508, 0.817] / 0.484 [0.349, 0.659] | 0.952 [0.849, 0.984] / 0.778 [0.667, 0.841] | 0.802 [0.722, 0.897] / 0.635 [0.548, 0.746] | 0.673 [0.510, 0.746] / 0.515 [0.355, 0.595] |
| none | adaptive | multichart | 0.738 [0.603, 0.849] / 0.540 [0.413, 0.659] | 0.897 [0.754, 0.944] / 0.706 [0.571, 0.786] | 0.635 [0.548, 0.730] / 0.468 [0.381, 0.563] | 0.586 [0.472, 0.661] / 0.419 [0.310, 0.500] |
| none | _r0 | nothing | 0.857 [0.738, 0.952] / 0.857 [0.738, 0.952] | 0.937 [0.881, 0.976] / 0.937 [0.881, 0.976] | 0.905 [0.841, 0.960] / 0.905 [0.841, 0.960] | 0.873 [0.738, 0.921] / 0.873 [0.738, 0.921] |
| none | _r0 | max | 0.675 [0.508, 0.817] / 0.516 [0.349, 0.651] | 0.778 [0.595, 0.849] / 0.611 [0.460, 0.698] | 0.429 [0.341, 0.571] / 0.317 [0.246, 0.437] | 0.476 [0.323, 0.548] / 0.341 [0.214, 0.405] |
| none | _r0 | cusum | 0.579 [0.468, 0.770] / 0.413 [0.310, 0.611] | 0.905 [0.810, 0.960] / 0.730 [0.611, 0.810] | 0.746 [0.651, 0.825] / 0.587 [0.492, 0.683] | 0.616 [0.447, 0.690] / 0.458 [0.302, 0.536] |
| none | _r0 | multichart | 0.651 [0.540, 0.786] / 0.476 [0.365, 0.603] | 0.833 [0.698, 0.897] / 0.651 [0.524, 0.730] | 0.548 [0.452, 0.643] / 0.389 [0.294, 0.484] | 0.507 [0.393, 0.583] / 0.348 [0.246, 0.421] |

## Adaptive − one-shot (matched diagonal), alpha = 0.01

| mode | arm | detector | judge | strict |
|---|---|---|---|---|
| full | max | max | +0.159 [+0.095, +0.230] | +0.151 [+0.095, +0.222] |
| full | cusum | cusum | +0.095 [+0.032, +0.143] | +0.087 [+0.032, +0.127] |
| full | multichart | multichart | +0.167 [+0.095, +0.222] | +0.151 [+0.084, +0.206] |
| none | max | max | +0.032 [-0.048, +0.111] | +0.024 [-0.056, +0.111] |
| none | cusum | cusum | +0.048 [+0.000, +0.087] | +0.048 [+0.000, +0.087] |
| none | multichart | multichart | +0.079 [+0.024, +0.143] | +0.071 [+0.016, +0.131] |

## M3 — round-1 arms re-expressed relative to the round-2 rewrite-only control (monitor gpt-4.1 none, paired n = 126)

Only identifiable under the round-2 monitor, and only approximately: the control used the round-2 pipeline (JSON mode, 90% length floor, no condensation), and the round-1 adaptive arms selected on gpt-4.1-mini feedback. The one-shot (r0) rows are the cleaner comparison.

| comparison | detector | alpha | judge | strict |
|---|---|---|---|---|
| r1_max_r0 - rewrite_control | max | 0.01 | +0.095 [+0.008, +0.183] | +0.079 [-0.008, +0.159] |
| r1_max_r0 - rewrite_control | multichart | 0.01 | +0.046 [-0.073, +0.107] | +0.030 [-0.074, +0.090] |
| r1_max_r0 - rewrite_control | top3sum | 0.01 | +0.040 [-0.032, +0.143] | +0.024 [-0.056, +0.111] |
| r1_cusum_r0 - rewrite_control | max | 0.01 | +0.087 [-0.024, +0.159] | +0.071 [-0.032, +0.135] |
| r1_cusum_r0 - rewrite_control | multichart | 0.01 | +0.044 [-0.044, +0.135] | +0.036 [-0.041, +0.121] |
| r1_cusum_r0 - rewrite_control | top3sum | 0.01 | +0.087 [+0.016, +0.190] | +0.071 [+0.000, +0.167] |
| r1_multichart_r0 - rewrite_control | max | 0.01 | +0.063 [-0.032, +0.143] | +0.032 [-0.056, +0.103] |
| r1_multichart_r0 - rewrite_control | multichart | 0.01 | +0.032 [-0.063, +0.127] | +0.016 [-0.069, +0.099] |
| r1_multichart_r0 - rewrite_control | top3sum | 0.01 | +0.040 [-0.040, +0.151] | +0.008 [-0.063, +0.103] |
| r1_max - rewrite_control | max | 0.01 | +0.135 [+0.048, +0.214] | +0.119 [+0.040, +0.190] |
| r1_max - rewrite_control | multichart | 0.01 | +0.093 [-0.008, +0.167] | +0.077 [-0.010, +0.151] |
| r1_max - rewrite_control | top3sum | 0.01 | +0.095 [+0.024, +0.198] | +0.071 [+0.008, +0.167] |
| r1_cusum - rewrite_control | max | 0.01 | +0.063 [-0.040, +0.151] | +0.056 [-0.040, +0.135] |
| r1_cusum - rewrite_control | multichart | 0.01 | +0.052 [-0.054, +0.145] | +0.036 [-0.057, +0.132] |
| r1_cusum - rewrite_control | top3sum | 0.01 | +0.119 [+0.048, +0.222] | +0.095 [+0.024, +0.190] |
| r1_multichart - rewrite_control | max | 0.01 | +0.111 [+0.016, +0.206] | +0.071 [-0.016, +0.159] |
| r1_multichart - rewrite_control | multichart | 0.01 | +0.099 [-0.008, +0.182] | +0.060 [-0.036, +0.137] |
| r1_multichart - rewrite_control | top3sum | 0.01 | +0.103 [+0.032, +0.214] | +0.056 [-0.008, +0.159] |
| r1_max_r0 - nothing | max | 0.01 | -0.262 [-0.349, -0.151] | -0.421 [-0.508, -0.310] |
| r1_max_r0 - nothing | multichart | 0.01 | -0.284 [-0.403, -0.203] | -0.442 [-0.554, -0.357] |
| r1_max_r0 - nothing | top3sum | 0.01 | -0.310 [-0.429, -0.198] | -0.460 [-0.571, -0.349] |
| r1_max - nothing | max | 0.01 | -0.222 [-0.294, -0.119] | -0.381 [-0.460, -0.278] |
| r1_max - nothing | multichart | 0.01 | -0.236 [-0.335, -0.159] | -0.395 [-0.488, -0.304] |
| r1_max - nothing | top3sum | 0.01 | -0.254 [-0.349, -0.151] | -0.413 [-0.508, -0.302] |

## Covert sqrt(ARL) slopes re-fit on the calibratable range (ARL <= 551)

| run | sweep | n | slope (project, ARL to 1e4) | slope (ARL <= 551) |
|---|---|---|---|---|
| full_adaptive | covert_nothing | 150 | 0.003 | 0.007 |
| full_adaptive | covert_cusum | 129 | 0.008 | 0.013 |
| full_adaptive | covert_multichart | 141 | 0.030 | 0.015 |
| full_r0 | covert_nothing | 150 | 0.003 | 0.007 |
| full_r0 | covert_cusum | 128 | 0.013 | 0.023 |
| full_r0 | covert_multichart | 131 | 0.040 | 0.027 |
| none_adaptive | covert_nothing | 150 | 0.010 | 0.024 |
| none_adaptive | covert_cusum | 129 | 0.005 | 0.016 |
| none_adaptive | covert_multichart | 141 | 0.027 | 0.036 |
| none_r0 | covert_nothing | 150 | 0.010 | 0.024 |
| none_r0 | covert_cusum | 128 | 0.007 | 0.021 |
| none_r0 | covert_multichart | 131 | 0.031 | 0.045 |

## m5 — held-out honest FPR (gpt-4.1-mini; 275/275 splits x 200)

| mode | detector | alpha | mean realized FPR | 5%–95% | mean / nominal |
|---|---|---|---|---|---|
| full | max | 0.01 | 0.0108 | 0.0000–0.0291 | 1.08 |
| full | max | 0.003 | 0.0037 | 0.0000–0.0145 | 1.24 |
| full | cusum | 0.01 | 0.0100 | 0.0000–0.0220 | 1.00 |
| full | cusum | 0.003 | 0.0036 | 0.0000–0.0111 | 1.19 |
| full | eprocess | 0.01 | 0.0103 | 0.0000–0.0291 | 1.03 |
| full | eprocess | 0.003 | 0.0033 | 0.0000–0.0111 | 1.08 |
| full | multichart | 0.01 | 0.0179 | 0.0036–0.0382 | 1.79 |
| full | multichart | 0.003 | 0.0124 | 0.0019–0.0265 | 4.12 |
| none | max | 0.01 | 0.0105 | 0.0000–0.0255 | 1.05 |
| none | max | 0.003 | 0.0034 | 0.0000–0.0145 | 1.14 |
| none | cusum | 0.01 | 0.0105 | 0.0000–0.0291 | 1.05 |
| none | cusum | 0.003 | 0.0037 | 0.0000–0.0109 | 1.24 |
| none | eprocess | 0.01 | 0.0122 | 0.0000–0.0327 | 1.22 |
| none | eprocess | 0.003 | 0.0043 | 0.0000–0.0145 | 1.42 |
| none | multichart | 0.01 | 0.0198 | 0.0064–0.0382 | 1.98 |
| none | multichart | 0.003 | 0.0127 | 0.0015–0.0292 | 4.24 |

## m6 — submit stripping: streams changed per arm; max |effect| on any point estimate = 0

| mode | arm | variant | n | changed | lacking meta.literals_missing (recomputed) |
|---|---|---|---|---|---|
| full | max | adaptive | 145 | 2 | 4 |
| full | cusum | adaptive | 131 | 1 | 4 |
| full | multichart | adaptive | 143 | 4 | 4 |
| full | max | _r0 | 145 | 2 | 4 |
| full | cusum | _r0 | 131 | 0 | 4 |
| full | multichart | _r0 | 143 | 2 | 4 |
| none | max | adaptive | 145 | 2 | 4 |
| none | cusum | adaptive | 131 | 1 | 4 |
| none | multichart | adaptive | 143 | 4 | 4 |
| none | max | _r0 | 145 | 2 | 4 |
| none | cusum | _r0 | 131 | 0 | 4 |
| none | multichart | _r0 | 143 | 2 | 4 |
