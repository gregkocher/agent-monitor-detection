# Track 3 — monitor-aware attacker: results

Monitor `openai/gpt-4.1-mini` (`ctrl-basic-v1`, action-only); detectors calibrated on Honest-550 at matched trajectory FPR (randomized thresholds, alpha in {0.01,0.003}). Base attacks: 150 MonitoringBench S2-S4 within track-1's scored sample; **paired comparison on the 126 base attacks produced by every arm**. Undetected-success = E[valid x (1-P(alarm))]; 95% bootstrap CIs over base attacks. t3 spend $68.4.

## Headline findings

- **Detector-aware refinement did NOT help and usually HURT the attacker on this (weak) monitor.** Catch rate on the ORIGINAL attacks at 1% FPR is only max 14%, cusum 4%, eprocess 8%, multichart 15%: originals already evade via length/dilution. The refiner condensed attacks (steps added -14..-15; length ratio 0.58..0.83), concentrating malicious actions and RAISING per-step max suspicion (orig 5.8 -> max-aware 7.6); undetected-success vs multichart fell from 0.85 (original) to 0.68 (multichart-aware).
- **CUSUM-alone is the weakest, most-evadable detector** (cusum-aware vs cusum = 0.86 undetected); **max and the multi-chart OR are strongest**; the OR keeps undetected-success lowest vs the max/multichart-aware attackers (0.49/0.68) -- it closes CUSUM's gap but ~ties max.
- **Adaptive (2 feedback rounds) beats one-shot** by +0.10..+0.17 undetected-success on the matched diagonal (multichart-aware vs multichart 0.51 -> 0.68), yet still underperforms the original.
- **Covert sqrt(ARL) test:** undetected damage is FLAT in ARL over 10^1.5-10^4 (slopes 0.00-0.03 << 0.5): attacks sit below the detectability band, so damage saturates rather than growing like sqrt(ARL).
- **Validity:** judge preservation 99%/98%/99%; literal preservation 0.89/0.90/0.88 (max/cusum/multichart). Undetected-success drops are genuine detection, not broken attacks.
- **Caveats:** weak monitor (AUROC~0.76-0.83); fabricated tool outputs for new steps (affects `full` more than `none`); BashArena Docker replay deferred (disk-constrained laptop).

## Attacker cost (full, adaptive)

| arm | n | length ratio | steps added | attack-rel steps |
|---|---|---|---|---|
| max | 145 | 0.63 | -14.0 | 5.7 |
| cusum | 131 | 0.83 | -7.8 | 4.1 |
| multichart | 143 | 0.58 | -15.3 | 4.2 |

## Covert damage scaling (slope of log-damage vs log-ARL; sqrt(ARL) => 0.5)

| attacker | monitor | n | slope | dmg@ARL~32 | dmg@ARL~1e4 |
|---|---|---|---|---|---|
| naive | full | 150 | 0.003 | 6.6 | 6.8 |
| cusum-aware | full | 129 | 0.008 | 3.9 | 4.1 |
| multichart-aware | full | 141 | 0.030 | 3.6 | 4.2 |
| naive | none | 150 | 0.010 | 6.3 | 6.8 |
| cusum-aware | none | 129 | 0.005 | 3.9 | 4.1 |
| multichart-aware | none | 141 | 0.027 | 3.6 | 4.2 |

## Full cross tables (undetected-success)

### Undetected-success rate — full monitor, adaptive


**alpha = 0.01**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.86 [0.79,0.91] | 0.96 [0.92,0.99] | 0.92 [0.87,0.97] | 0.85 [0.79,0.91] |
| max | 0.69 [0.60,0.78] | 0.74 [0.66,0.81] | 0.47 [0.38,0.56] | 0.49 [0.41,0.57] |
| cusum | 0.63 [0.56,0.71] | 0.86 [0.79,0.92] | 0.70 [0.61,0.78] | 0.58 [0.49,0.66] |
| multichart | 0.73 [0.65,0.81] | 0.81 [0.74,0.87] | 0.66 [0.58,0.74] | 0.68 [0.59,0.76] |

**alpha = 0.003**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.88 [0.83,0.94] | 0.98 [0.94,1.00] | 0.94 [0.89,0.98] | 0.87 [0.81,0.93] |
| max | 0.75 [0.68,0.83] | 0.85 [0.79,0.91] | 0.53 [0.44,0.62] | 0.52 [0.44,0.61] |
| cusum | 0.67 [0.60,0.75] | 0.90 [0.85,0.95] | 0.75 [0.67,0.82] | 0.62 [0.54,0.70] |
| multichart | 0.75 [0.67,0.83] | 0.89 [0.83,0.94] | 0.74 [0.67,0.81] | 0.71 [0.63,0.79] |

### Undetected-success rate — full monitor, _r0


**alpha = 0.01**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.86 [0.79,0.91] | 0.96 [0.92,0.99] | 0.92 [0.87,0.97] | 0.85 [0.79,0.91] |
| max | 0.53 [0.44,0.62] | 0.61 [0.52,0.70] | 0.37 [0.29,0.45] | 0.37 [0.29,0.46] |
| cusum | 0.60 [0.51,0.68] | 0.76 [0.69,0.83] | 0.64 [0.56,0.72] | 0.54 [0.45,0.63] |
| multichart | 0.58 [0.49,0.67] | 0.73 [0.65,0.81] | 0.53 [0.44,0.62] | 0.51 [0.43,0.59] |

**alpha = 0.003**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.88 [0.83,0.94] | 0.98 [0.94,1.00] | 0.94 [0.89,0.98] | 0.87 [0.81,0.93] |
| max | 0.58 [0.50,0.67] | 0.72 [0.65,0.80] | 0.40 [0.32,0.49] | 0.38 [0.30,0.47] |
| cusum | 0.66 [0.57,0.74] | 0.84 [0.77,0.90] | 0.68 [0.60,0.75] | 0.58 [0.49,0.66] |
| multichart | 0.61 [0.52,0.70] | 0.83 [0.75,0.89] | 0.60 [0.52,0.68] | 0.56 [0.48,0.65] |

### Undetected-success rate — none monitor, adaptive


**alpha = 0.01**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.86 [0.79,0.91] | 0.94 [0.89,0.98] | 0.90 [0.85,0.95] | 0.87 [0.81,0.93] |
| max | 0.71 [0.63,0.79] | 0.81 [0.74,0.87] | 0.50 [0.41,0.59] | 0.53 [0.44,0.61] |
| cusum | 0.65 [0.57,0.74] | 0.95 [0.91,0.98] | 0.80 [0.73,0.87] | 0.67 [0.59,0.75] |
| multichart | 0.74 [0.66,0.81] | 0.90 [0.84,0.94] | 0.63 [0.56,0.71] | 0.59 [0.50,0.67] |

**alpha = 0.003**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.93 [0.88,0.97] | 0.96 [0.92,0.99] | 0.92 [0.87,0.96] | 0.88 [0.83,0.94] |
| max | 0.85 [0.79,0.90] | 0.92 [0.87,0.96] | 0.59 [0.50,0.67] | 0.56 [0.47,0.64] |
| cusum | 0.78 [0.71,0.85] | 0.97 [0.94,0.99] | 0.86 [0.79,0.91] | 0.69 [0.62,0.77] |
| multichart | 0.84 [0.77,0.90] | 0.94 [0.89,0.98] | 0.67 [0.59,0.75] | 0.63 [0.55,0.71] |

### Undetected-success rate — none monitor, _r0


**alpha = 0.01**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.86 [0.79,0.91] | 0.94 [0.89,0.98] | 0.90 [0.85,0.95] | 0.87 [0.81,0.93] |
| max | 0.67 [0.59,0.75] | 0.78 [0.70,0.85] | 0.43 [0.34,0.52] | 0.48 [0.39,0.56] |
| cusum | 0.58 [0.49,0.67] | 0.90 [0.85,0.95] | 0.75 [0.67,0.82] | 0.62 [0.53,0.70] |
| multichart | 0.65 [0.56,0.74] | 0.83 [0.76,0.90] | 0.55 [0.46,0.63] | 0.51 [0.42,0.59] |

**alpha = 0.003**

| attacker \ deployed | max | cusum | eprocess | multichart |
|---|---|---|---|---|
| nothing | 0.93 [0.88,0.97] | 0.96 [0.92,0.99] | 0.92 [0.87,0.96] | 0.88 [0.83,0.94] |
| max | 0.78 [0.71,0.85] | 0.82 [0.75,0.88] | 0.53 [0.44,0.62] | 0.50 [0.41,0.58] |
| cusum | 0.73 [0.65,0.80] | 0.95 [0.91,0.98] | 0.79 [0.71,0.86] | 0.64 [0.55,0.71] |
| multichart | 0.75 [0.67,0.82] | 0.87 [0.80,0.92] | 0.57 [0.49,0.66] | 0.54 [0.46,0.62] |
