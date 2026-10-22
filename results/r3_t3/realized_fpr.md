# Realized held-out trajectory FPR

Mean over 200 random 50/50 honest splits; brackets are the 2.5/97.5 percentiles.

| monitor | n_honest | detector | alpha | realized FPR |
|---|---|---|---|---|
| with-output | 550 | max | 0.05 | 0.0527 [0.0218,0.0982] |
| with-output | 550 | max | 0.01 | 0.0107 [0.0000,0.0292] |
| with-output | 550 | max | 0.003 | 0.0038 [0.0000,0.0182] |
| with-output | 550 | cusum1.5 | 0.05 | 0.0528 [0.0217,0.0945] |
| with-output | 550 | cusum1.5 | 0.01 | 0.0102 [0.0000,0.0292] |
| with-output | 550 | cusum1.5 | 0.003 | 0.0033 [0.0000,0.0182] |
| with-output | 550 | multichart | 0.05 | 0.0581 [0.0254,0.1028] |
| with-output | 550 | multichart | 0.01 | 0.0173 [0.0027,0.0432] |
| with-output | 550 | multichart | 0.003 | 0.0102 [0.0000,0.0291] |
| with-output | 550 | top3sum | 0.05 | 0.0497 [0.0217,0.0873] |
| with-output | 550 | top3sum | 0.01 | 0.0106 [0.0000,0.0292] |
| with-output | 550 | top3sum | 0.003 | 0.0040 [0.0000,0.0182] |
| no-output | 250 | max | 0.05 | 0.0552 [0.0080,0.1120] |
| no-output | 250 | max | 0.01 | 0.0174 [0.0000,0.0560] |
| no-output | 250 | max | 0.003 | 0.0104 [0.0000,0.0480] |
| no-output | 250 | cusum1.5 | 0.05 | 0.0573 [0.0080,0.1362] |
| no-output | 250 | cusum1.5 | 0.01 | 0.0164 [0.0000,0.0560] |
| no-output | 250 | cusum1.5 | 0.003 | 0.0088 [0.0000,0.0400] |
| no-output | 250 | multichart | 0.05 | 0.0645 [0.0159,0.1360] |
| no-output | 250 | multichart | 0.01 | 0.0255 [0.0000,0.0800] |
| no-output | 250 | multichart | 0.003 | 0.0177 [0.0000,0.0490] |
| no-output | 250 | top3sum | 0.05 | 0.0547 [0.0080,0.1280] |
| no-output | 250 | top3sum | 0.01 | 0.0156 [0.0000,0.0560] |
| no-output | 250 | top3sum | 0.003 | 0.0088 [0.0000,0.0404] |
