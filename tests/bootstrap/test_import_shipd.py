from pathlib import Path

import numpy as np
import pytest

from magnet.bootstrap.import_shipd import ShipDImporter


def test_import_vectors_from_explicit_file(tmp_path: Path):
    X = np.random.default_rng(0).normal(size=(5, 45)).astype(float)
    p = tmp_path / "InputVectors_30k.npy"
    np.save(p, X)

    importer = ShipDImporter(shipd_root=tmp_path)
    hulls = importer.import_vectors(vector_file=p)
    assert len(hulls) == 5
    assert hulls[0].hull_id == "shipd:0"
    assert hulls[0].vector.shape == (45,)
    assert hulls[0].source_path.endswith("InputVectors_30k.npy")


def test_import_vectors_respects_limit(tmp_path: Path):
    X = np.zeros((10, 45), dtype=float)
    p = tmp_path / "InputVectors_30k.npy"
    np.save(p, X)

    importer = ShipDImporter(shipd_root=tmp_path)
    hulls = importer.import_vectors(vector_file=p, limit=3)
    assert len(hulls) == 3


def test_find_vector_file_raises_when_missing(tmp_path: Path):
    importer = ShipDImporter(shipd_root=tmp_path)
    with pytest.raises(FileNotFoundError):
        importer.find_vector_file()

