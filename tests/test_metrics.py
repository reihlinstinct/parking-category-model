import numpy as np

from parking_category_model import metrics


def test_confusion_and_report():
    m = metrics.confusion_matrix(np.array([0, 0, 1, 1]), np.array([0, 1, 1, 1]), 3)
    assert m.tolist() == [[1, 1, 0], [0, 2, 0], [0, 0, 0]]
    assert metrics.accuracy(m) == 0.75
    report = metrics.per_class_report(m, ["a", "b", "c"])
    assert report["b"]["precision"] == 2 / 3
    assert report["a"]["recall"] == 0.5
    assert report["c"]["f1"] == 0.0
