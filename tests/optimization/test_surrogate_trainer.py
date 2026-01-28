import numpy as np

from magnet.optimization.surrogate_trainer import TrainingRecord, SurrogateTrainer


def test_surrogate_trainer_trains_models_per_objective():
    trainer = SurrogateTrainer(param_names=["x"], objectives=["y"])
    records = [
        TrainingRecord(params={"x": 0.0}, objectives={"y": 0.0}),
        TrainingRecord(params={"x": 1.0}, objectives={"y": 1.0}),
        TrainingRecord(params={"x": 2.0}, objectives={"y": 4.0}),
        TrainingRecord(params={"x": 3.0}, objectives={"y": 9.0}),
    ]
    res = trainer.train(records)
    assert res.n_samples == 4
    assert "y" in res.models

    m = res.models["y"]
    mean, std = m.predict(np.array([[1.5]]))
    assert mean.shape == (1,)
    assert std.shape == (1,)

