import numpy as np

from magnet.optimization.surrogate_model import SurrogateModel


def test_botorch_backend_request_gracefully_falls_back_when_unavailable():
    """
    Phase 2 (BoTorch integration): requesting BoTorch must not break the suite
    when BoTorch isn't installed. The SurrogateModel should fall back to sklearn.
    """
    X = np.array([[0.0], [1.0], [2.0], [3.0]], dtype=float)
    y = np.array([0.0, 1.0, 0.5, 1.5], dtype=float)

    m = SurrogateModel(backend="botorch", parameter_names=["x"], objective_name="y")
    m.fit(X, y)
    mean, std = m.predict(np.array([[1.5]], dtype=float))

    assert mean.shape == (1,)
    assert std.shape == (1,)
    # If BoTorch isn't installed, we should have fallen back.
    assert str(m.backend).lower() in ("botorch", "sklearn")

