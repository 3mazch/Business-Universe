import os
import random
import pandas as pd
import numpy as np

# Resolve PROJECT_ROOT by going up two levels from this file (src/data_generation/config.py)
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(THIS_DIR))

# Common Seeds and Constants
RNG_SEED = 42

# Data Directories
DIM_FULL_DIR = os.path.join(PROJECT_ROOT, "data", "dimension", "full")
DIM_SAMPLE_DIR = os.path.join(PROJECT_ROOT, "data", "dimension", "sample")
DIM_TEMP_DIR = os.path.join(PROJECT_ROOT, "data", "dimension", "temp")

os.makedirs(DIM_FULL_DIR, exist_ok=True)
os.makedirs(DIM_SAMPLE_DIR, exist_ok=True)
os.makedirs(DIM_TEMP_DIR, exist_ok=True)

def save_dimension(df: pd.DataFrame, filename: str):
    """
    Saves a dimension DataFrame to both the full directory and the sample directory.
    The sample directory keeps only up to 100 random or head lines to reduce size for git.
    """
    full_path = os.path.join(DIM_FULL_DIR, filename)
    sample_path = os.path.join(DIM_SAMPLE_DIR, filename)
    
    # Save full
    df.to_csv(full_path, index=False, encoding="utf-8-sig")
    print(f"Saved full dimension to: {full_path}")
    
    # Save sample (max 100 rows)
    df_sample = df.head(100) if len(df) > 100 else df
    df_sample.to_csv(sample_path, index=False, encoding="utf-8-sig")
    print(f"Saved sample dimension to: {sample_path}")

def save_temp(df: pd.DataFrame, filename: str):
    """Saves an intermediate file to the temp directory."""
    temp_path = os.path.join(DIM_TEMP_DIR, filename)
    df.to_csv(temp_path, index=False, encoding="utf-8-sig")
    print(f"Saved temp file to: {temp_path}")

def load_temp(filename: str) -> pd.DataFrame:
    """Loads an intermediate file from the temp directory."""
    temp_path = os.path.join(DIM_TEMP_DIR, filename)
    return pd.read_csv(temp_path)

def get_global_rng(seed: int = RNG_SEED):
    random.seed(seed)
    np.random.seed(seed)
    return random, np.random.default_rng(seed)
