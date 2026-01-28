import numpy as np

from magnet.optimization.surrogate_model import SurrogateModel


def test_surrogate_model_fit_predict_shapes_and_uncertainty():
    # Simple 1D function: y = sin(x)
    xs = np.linspace(0.0, 2.0 * np.pi, 12)
    X = xs.reshape(-1, 1)
    y = np.sin(xs)

    m = SurrogateModel(parameter_names=["x"], objective_name="sin")
    m.fit(X, y)

    mean, std = m.predict(np.array([[0.1], [1.2], [3.4]]))
    assert mean.shape == (3,)
    assert std.shape == (3,)
    assert np.all(std >= 0.0)

    # Uncertainty at/near a training point should be <= uncertainty far away
    mean0, std0 = m.predict(np.array([[xs[0]]]))
    mean_far, std_far = m.predict(np.array([[100.0]]))
    assert float(std0[0]) <= float(std_far[0]) + 1e-9


def test_surrogate_model_gradient_is_finite():
    xs = np.linspace(-1.0, 1.0, 9)
    X = xs.reshape(-1, 1)
    y = xs ** 2

    m = SurrogateModel(parameter_names=["x"], objective_name="square")
    m.fit(X, y)

    g = m.compute_gradient(np.array([0.25]))
    assert g.shape == (1,)
    assert np.isfinite(g[0])


def test_surrogate_model_acquisition_value_is_non_negative():
    xs = np.linspace(0.0, 1.0, 6)
    X = xs.reshape(-1, 1)
    y = xs

    m = SurrogateModel(parameter_names=["x"], objective_name="linear")
    m.fit(X, y)

    ei = m.acquisition_value(np.array([0.5]), best_y=float(np.max(y)), exploration_weight=0.01)
    assert np.isfinite(ei)
    assert ei >= 0.0

