"""Matched-budget calibration, streaming metrics, Logit-ROC extrapolation, per-context
threshold allocation, and synthetic streams. See docs/detectors.md."""
from .calibration import Threshold, calibrate, conformal_threshold, randomized_threshold
from .contexts import (context_curve, cfar_thresholds, evaluate_thresholds, global_threshold,
                       max_detection_allocation, partially_pooled_thresholds,
                       stackelberg_thresholds)
from .logit_roc import LogitROCFit, empirical_roc, logit_roc_extrapolate, logit_roc_fit
from .matched import (bootstrap_weights, crossfit_models, crossfit_stats, matched_budget_eval,
                      score_with_models, simple_matched)
from .streaming import (alarm_times, arl0_simulation, delay_summary, delay_table,
                        localization_errors, trajectory_arl)

__all__ = [
    "Threshold", "calibrate", "conformal_threshold", "randomized_threshold",
    "matched_budget_eval", "simple_matched", "crossfit_stats", "crossfit_models",
    "score_with_models", "bootstrap_weights",
    "alarm_times", "delay_table", "delay_summary", "arl0_simulation", "localization_errors",
    "trajectory_arl",
    "LogitROCFit", "empirical_roc", "logit_roc_fit", "logit_roc_extrapolate",
    "context_curve", "global_threshold", "cfar_thresholds", "partially_pooled_thresholds",
    "max_detection_allocation", "stackelberg_thresholds", "evaluate_thresholds",
]
