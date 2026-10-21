# Length-aware hybrids: mean TPR gain over max across stream sets

| alpha | detector | all sets: mean gain | sets with |log len ratio| > 0.2: mean gain (n) | win/loss (>0.01) |
|---|---|---|---|---|
| 0.01 | kth2 | -0.026 | -0.027 (29) | 18/23 |
| 0.01 | lenbin(kth2) | -0.111 | -0.116 (29) | 9/33 |
| 0.01 | lenbin(max) | -0.122 | -0.142 (29) | 5/39 |
| 0.01 | lenbin(top3sum) | -0.152 | -0.187 (29) | 7/35 |
| 0.01 | max_lenaware | -0.011 | +0.008 (29) | 19/23 |
| 0.01 | top3sum | -0.032 | -0.045 (29) | 16/24 |
| 0.05 | kth2 | -0.032 | -0.024 (29) | 10/28 |
| 0.05 | lenbin(kth2) | -0.047 | -0.025 (29) | 9/32 |
| 0.05 | lenbin(max) | -0.028 | -0.024 (29) | 7/21 |
| 0.05 | lenbin(top3sum) | -0.019 | -0.021 (29) | 14/24 |
| 0.05 | max_lenaware | +0.013 | +0.028 (29) | 13/15 |
| 0.05 | top3sum | -0.010 | -0.020 (29) | 13/26 |

Realized FPR (mean over sets) at alpha: kth2@0.01: 0.014, lenbin(kth2)@0.01: 0.011, lenbin(max)@0.01: 0.010, lenbin(top3sum)@0.01: 0.011, max@0.01: 0.012, max_lenaware@0.01: 0.011, top3sum@0.01: 0.013, kth2@0.05: 0.053, lenbin(kth2)@0.05: 0.049, lenbin(max)@0.05: 0.048, lenbin(top3sum)@0.05: 0.050, max@0.05: 0.051, max_lenaware@0.05: 0.050, top3sum@0.05: 0.051
