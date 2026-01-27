import numpy as np

from magnet.bootstrap.embeddings import HashEmbedding, build_hull_signature_text, embed_hull_signatures


def test_hash_embedding_is_deterministic_and_normalized():
    emb = HashEmbedding(dim=64)
    v1 = emb.embed("hello")
    v2 = emb.embed("hello")
    v3 = emb.embed("different")

    assert v1.shape == (64,)
    assert np.allclose(v1, v2)
    assert not np.allclose(v1, v3)

    # roughly unit norm for cosine similarity use
    assert abs(float(np.linalg.norm(v1)) - 1.0) < 1e-8


def test_build_hull_signature_text_is_stable():
    t = build_hull_signature_text(hull_id="shipd:0", params=[0.1, -2.0, 3.0], max_params=2)
    assert "hull_id=shipd:0" in t
    assert "p[:2]=" in t


def test_embed_hull_signatures_batch_shape():
    provider = HashEmbedding(dim=32)
    X = embed_hull_signatures(
        hull_ids=["a", "b", "c"],
        vectors=[[0.0] * 45, [1.0] * 45, [2.0] * 45],
        provider=provider,
        max_params=4,
    )
    assert X.shape == (3, 32)

