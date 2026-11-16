"""Pure-numpy evaluation metrics."""

from __future__ import annotations

import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> np.ndarray:
    """Rows are true classes, columns are predicted classes."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true and y_pred must have the same shape")
    matrix = np.zeros((n_classes, n_classes), dtype=int)
    np.add.at(matrix, (y_true, y_pred), 1)
    return matrix


def per_class_report(matrix: np.ndarray, names: list[str]) -> dict[str, dict[str, float]]:
    """Precision, recall and F1 per class. Undefined ratios are reported as 0.0."""
    report: dict[str, dict[str, float]] = {}
    for i, name in enumerate(names):
        tp = float(matrix[i, i])
        predicted = float(matrix[:, i].sum())
        actual = float(matrix[i, :].sum())
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        report[name] = {"precision": precision, "recall": recall, "f1": f1, "support": actual}
    return report


def accuracy(matrix: np.ndarray) -> float:
    total = matrix.sum()
    return float(np.trace(matrix) / total) if total else 0.0
