# Paired differences in undetected-success (gpt-4.1, none, adaptive; n=126; 95% bootstrap CI over base attacks)

| comparison | detector | alpha | diff [95% CI] |
|---|---|---|---|
| pace_max − nothing | max | 0.01 | -0.151 [-0.254,-0.056] |
| pace_max − r1_max | max | 0.01 | +0.071 [-0.016,+0.159] |
| pace_max − rewrite_control | max | 0.01 | +0.206 [+0.119,+0.294] |
| pace_cusum − r1_cusum | cusum1.5 | 0.01 | +0.016 [-0.071,+0.103] |
| pace_cusum − rewrite_control | cusum1.5 | 0.01 | +0.071 [-0.024,+0.159] |
| pace_multichart − nothing | multichart | 0.01 | -0.153 [-0.238,-0.069] |
| pace_multichart − r1_multichart | multichart | 0.01 | +0.077 [-0.006,+0.161] |
| pace_multichart − rewrite_control | multichart | 0.01 | +0.177 [+0.095,+0.258] |
| rewrite_control − nothing | max | 0.01 | -0.357 [-0.452,-0.262] |
| pace_max − rewrite_control | top3sum | 0.01 | +0.032 [-0.063,+0.127] |
| pace_max − nothing | max | 0.003 | -0.079 [-0.159,+0.000] |
| pace_max − r1_max | max | 0.003 | +0.087 [+0.008,+0.167] |
| pace_max − rewrite_control | max | 0.003 | +0.214 [+0.143,+0.294] |
| pace_cusum − r1_cusum | cusum1.5 | 0.003 | -0.103 [-0.183,-0.024] |
| pace_cusum − rewrite_control | cusum1.5 | 0.003 | +0.032 [-0.063,+0.127] |
| pace_multichart − nothing | multichart | 0.003 | -0.070 [-0.151,+0.011] |
| pace_multichart − r1_multichart | multichart | 0.003 | +0.104 [+0.032,+0.179] |
| pace_multichart − rewrite_control | multichart | 0.003 | +0.196 [+0.110,+0.278] |
| rewrite_control − nothing | max | 0.003 | -0.294 [-0.381,-0.206] |
| pace_max − rewrite_control | top3sum | 0.003 | +0.048 [-0.040,+0.127] |
