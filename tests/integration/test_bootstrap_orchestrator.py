import numpy as np

from magnet.bootstrap.orchestrator import BootstrapOrchestrator


def test_bootstrap_orchestrator_builds_shipd_library_and_embeddings(tmp_path):
    shipd_root = tmp_path / "shipd"
    shipd_root.mkdir(parents=True, exist_ok=True)

    vec_path = shipd_root / "input_vectors.npy"
    X = np.asarray(
        [
            [1.0, 2.0, 3.0, 4.0],
            [2.0, 3.0, 4.0, 5.0],
            [10.0, 20.0, 30.0, 40.0],
        ],
        dtype=float,
    )
    np.save(vec_path, X)

    orch = BootstrapOrchestrator()
    art = orch.build_shipd_library(shipd_root=shipd_root, vector_file=vec_path, limit=3)

    assert art.hull_ids == ["shipd:0", "shipd:1", "shipd:2"]
    assert art.parameter_names == ["p0", "p1", "p2", "p3"]

    # Embeddings should exist and be deterministic in shape.
    assert art.embeddings.ndim == 2
    assert art.embeddings.shape[0] == 3
    assert art.embeddings.shape[1] >= 8

    # Library should return the same parameterization.
    h0 = art.library.get("shipd:0").parameters
    assert h0 == {"p0": 1.0, "p1": 2.0, "p2": 3.0, "p3": 4.0}

