"""Synthetic financial customer twins for controlled product scenario testing."""

from .population import generate_population
from .simulation import default_product_variants, simulate_population

__all__ = ["default_product_variants", "generate_population", "simulate_population"]
__version__ = "0.1.0"
