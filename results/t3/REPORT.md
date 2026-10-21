# Track 3: monitor-aware attackers vs sequential detectors

The full write-up is the PDF `~/Desktop/monitoring-research/reports/03_Idea3_Aware_Attacker.pdf`. Tables are in `results/t3/tables.md` and `cross_table.csv`; figures are `results/t3/*.pdf`.

## Key findings

1. **Detector-aware rewriting did not help the attacker; it usually hurt.**
   - The attacker was gpt-4.1, given the monitor prompt and the exact detector rule, with up to 2 feedback rounds. It rewrote 150 MonitoringBench S2–S4 attacks.
   - Against max at 1% FPR, undetected success was 0.86 for the originals vs 0.63–0.73 for the aware arms.
   - The attacker condensed attacks (length ratio 0.58–0.83), which raised peak per-step suspicion from 5.8 to 7.6.
2. **Detector ranking.** CUSUM alone is the most evadable detector. Max and the multi-chart OR are strongest; the OR closes CUSUM's gap but roughly ties max.
3. **Feedback.** Adaptive feedback beats one-shot rewriting by +0.10 to +0.17, but still does not beat the originals.
4. **Covert √ARL test.** Undetected damage is flat in ARL (slope ≈ 0 vs 0.5 predicted). The weak monitor (AUROC 0.76–0.83) leaves attacks below the detectability band.
5. **Validity.**
   - LLM-judge preservation: 98–99%.
   - Literal-target preservation: 0.88–0.90.
   - There was no Docker replay (disk and VPN constraints).

Spend: $68.36.
