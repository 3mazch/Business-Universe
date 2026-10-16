"""
seed_utils.py — Reproducible, store-specific random number generation.
Flex Coffee & Tea Data Generation Engine v1.0

Strategy: dictionary-based XOR seed (not global).
seed(store_id, year, month) = (1000 + store_id * 37) XOR (year * 100 + month)
"""
import random
import numpy as np
from typing import Tuple


def get_seed(store_id: int, year: int, month: int) -> int:
    """Unique, reproducible seed for (store, year, month) combination."""
    store_base   = 1000 + store_id * 37
    month_offset = year * 100 + month
    return store_base ^ month_offset


def get_rng(store_id: int, year: int, month: int) -> Tuple[random.Random, np.random.Generator]:
    """
    Returns (stdlib_rng, numpy_rng) seeded for this (store, year, month).
    Use stdlib_rng for choices/weights; numpy_rng for distributions.
    """
    seed = get_seed(store_id, year, month)
    return random.Random(seed), np.random.default_rng(seed)


def get_global_rng(seed: int = 42) -> Tuple[random.Random, np.random.Generator]:
    """Global RNG for non-store-specific generation (e.g., dim tables)."""
    return random.Random(seed), np.random.default_rng(seed)
