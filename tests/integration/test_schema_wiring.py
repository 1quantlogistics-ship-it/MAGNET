"""
Schema wiring regression tests (enum-free synthesis surface).

These are lightweight import/wiring checks to catch accidental reintroduction
of legacy family/type synthesis contracts.
"""

from magnet.kernel.synthesis import HullSynthesizer, GeometrySynthesisRequest


def test_kernel_synthesis_imports_exist():
    # Importing these should succeed and define the public synthesis surface.
    assert HullSynthesizer is not None
    assert GeometrySynthesisRequest is not None

