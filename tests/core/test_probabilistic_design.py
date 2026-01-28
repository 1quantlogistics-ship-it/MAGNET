from magnet.core.probabilistic_design import NormalDistribution, ProbabilisticDesign


def test_probabilistic_design_expected_values_and_sampling():
    pd = ProbabilisticDesign(
        parameters={"x": NormalDistribution(mean=2.0, std=0.5)},
        objectives={"y": NormalDistribution(mean=10.0, std=1.0)},
    )
    assert pd.expected_parameters()["x"] == 2.0
    assert pd.expected_objectives()["y"] == 10.0

    samples = pd.sample_parameters(5, seed=123)
    assert len(samples) == 5
    assert all("x" in s for s in samples)


def test_confidence_interval():
    pd = ProbabilisticDesign(
        parameters={"x": NormalDistribution(mean=0.0, std=1.0)},
        objectives={},
    )
    lo, hi = pd.confidence_interval("x", level=0.95, where="parameters")
    assert lo < 0.0 < hi

