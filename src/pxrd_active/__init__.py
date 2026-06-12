"""Sequential-design tools for synthetic PXRD phase-mapping studies."""

from .mapping import MappingResult, run_mapping
from .synthetic import SyntheticPhaseMap, make_grid

__all__ = [
    "MappingResult",
    "SyntheticPhaseMap",
    "make_grid",
    "run_mapping",
]
