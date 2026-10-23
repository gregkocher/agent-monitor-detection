# Judge/literal/strict validity vs EXECUTION validity (rewrite arms)

false_valid = P(execution side_task fails | predicted valid). agree = overall match.

## rewrite_control (n=33, exec success rate 0.48484848484848486)
| predictor | agree | false_valid | tp | fp | fn | tn |
|---|---|---|---|---|---|---|
| judge | 0.394 | 0.571 | 12 | 16 | 4 | 1 |
| literal | 0.636 | 0.423 | 15 | 11 | 1 | 6 |
| strict | 0.515 | 0.500 | 11 | 11 | 5 | 6 |

## pace_max (n=28, exec success rate 0.39285714285714285)
| predictor | agree | false_valid | tp | fp | fn | tn |
|---|---|---|---|---|---|---|
| judge | 0.214 | 0.762 | 5 | 16 | 6 | 1 |
| literal | 0.536 | 0.545 | 10 | 12 | 1 | 5 |
| strict | 0.321 | 0.750 | 4 | 12 | 7 | 5 |

