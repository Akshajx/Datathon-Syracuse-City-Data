"""
prediction_pipeline.py
----------------------
Documented helpers for the Syracuse Code Violations vs Assessment project.

The main workflow lives in notebooks/Code_Violations_Assessment_Merge.ipynb; this module
captures column names and reusable building blocks so collaborators (and GitHub
readers) can see the ML contract without scrolling the whole notebook.

Usage (optional, from repo root):
    import sys
    sys.path.insert(0, "src")
    from utils.prediction_pipeline import FEATURE_COLUMNS, TARGET_COLUMN, build_parcel_dataframe
"""

from __future__ import annotations

import os
from typing import Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Repo root & data paths (override in notebook for Colab: point to your CSV dir)
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEFAULT_PROCESSED = os.path.join(_REPO_ROOT, "data", "processed", "Code_Violations_With_Assessment_2025.csv")
DEFAULT_MERGED_CSV = _DEFAULT_PROCESSED

# ---------------------------------------------------------------------------
# ML contract: what we predict and with what
# ---------------------------------------------------------------------------
# Target: city-assessed property value (continuous regression, NOT classification).
TARGET_COLUMN = "Assess_Total_Assessment"

# Features used in the Section 10 linear model (address / SBL / tax components excluded on purpose).
NUMERIC_FEATURES = ["violation_count", "open_count", "closed_count"]
CATEGORICAL_FEATURES = ["Assess_Prop_Class_Description", "Neighborhood"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# One-hot is correct for property class and neighborhood (nominal categories; no natural order).
# Label encoding would wrongly imply Apartment > 1 Family Res as a numeric scale.


def build_parcel_dataframe(merged: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate violation-level rows to one row per parcel (SBL).

    Parameters
    ----------
    merged : DataFrame
        Output of violations LEFT JOIN assessment on SBL; must include
        violation_id, status_type_name, Assess_Total_Assessment, and assessment columns.

    Returns
    -------
    parcel : DataFrame
        One row per SBL with violation counts and one assessment snapshot per parcel.
    """
    merged_valid = merged[merged[TARGET_COLUMN].notna()].copy()

    violation_counts = merged_valid.groupby("SBL").agg(
        violation_count=("violation_id", "count"),
        open_count=("status_type_name", lambda s: (s == "Open").sum()),
        closed_count=("status_type_name", lambda s: (s == "Closed").sum()),
    ).reset_index()

    assessment_cols = [
        "SBL",
        TARGET_COLUMN,
        "Assess_Prop_Class_Description",
        "Assess_Property_Class",
        "Neighborhood",
        "Assess_Property_Address",
        "Assess_School_Taxable",
        "Assess_Municipality_Taxable",
        "Assess_County_Taxable",
    ]
    parcel_assess = merged_valid.drop_duplicates(subset="SBL")[assessment_cols]

    parcel = parcel_assess.merge(violation_counts, on="SBL", how="left")
    for col in ("violation_count", "open_count", "closed_count"):
        parcel[col] = parcel[col].fillna(0).astype(int)

    return parcel


def load_merged_from_csv(path: str | None = None, low_memory: bool = False) -> pd.DataFrame:
    """Load the saved merged dataset (optional convenience for scripts)."""
    path = path or DEFAULT_MERGED_CSV
    return pd.read_csv(path, low_memory=low_memory)


def modeling_matrix(parcel: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Drop rows missing target or categoricals; return X and y for sklearn.

    Returns
    -------
    X : DataFrame with FEATURE_COLUMNS only
    y : ndarray of Assess_Total_Assessment
    """
    df = parcel.dropna(subset=[TARGET_COLUMN] + CATEGORICAL_FEATURES)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN].values
    return X, y
