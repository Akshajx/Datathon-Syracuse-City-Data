#!/usr/bin/env python3
"""
Regenerate EDA PNG into reports/figures/ (canonical) and mirror to docs/images/
for README + GitHub Pages.

Run from repo root: python -m src.data.export_preview_figures
"""
from __future__ import annotations

import os
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(_REPO_ROOT, "data", "raw")
REPORTS_FIG = os.path.join(_REPO_ROOT, "reports", "figures")
DOCS_IMG = os.path.join(_REPO_ROOT, "docs", "images")
os.makedirs(REPORTS_FIG, exist_ok=True)
os.makedirs(DOCS_IMG, exist_ok=True)


def load_merged() -> pd.DataFrame:
    vpath = os.path.join(RAW, "Code_Violations.csv")
    apath = os.path.join(RAW, "Assessment_Final_Roll_(2025).csv")
    if not os.path.isfile(vpath) or not os.path.isfile(apath):
        print("Missing data/raw CSVs:", vpath, apath, file=sys.stderr)
        sys.exit(1)

    violations = pd.read_csv(vpath, low_memory=False)
    assessment = pd.read_csv(apath, low_memory=False)
    violations["SBL"] = violations["SBL"].astype(str).str.strip()
    assessment["SBL"] = assessment["SBL"].astype(str).str.strip()

    assessment_sub = assessment.rename(
        columns={
            "Property_Address": "Assess_Property_Address",
            "Property_City": "Assess_Property_City",
            "Property_Class": "Assess_Property_Class",
            "Prop_Class_Description": "Assess_Prop_Class_Description",
            "Primary_Owner": "Assess_Primary_Owner",
            "Total_Assessment": "Assess_Total_Assessment",
            "School_Taxable": "Assess_School_Taxable",
            "Municipality_Taxable": "Assess_Municipality_Taxable",
            "County_Taxable": "Assess_County_Taxable",
        }
    )
    merged = violations.merge(assessment_sub, on="SBL", how="left", suffixes=("", "_assess"))
    if "ObjectId_assess" in merged.columns:
        merged = merged.drop(columns=["ObjectId_assess"])
    return merged


def main() -> None:
    merged = load_merged()
    merged["open_dt"] = pd.to_datetime(merged["open_date"], errors="coerce")
    merged["year"] = merged["open_dt"].dt.year

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    merged["year"].value_counts().sort_index().plot(kind="bar", ax=axes[0, 0], color="steelblue", edgecolor="black")
    axes[0, 0].set_title("Violations by year (open_date)")
    axes[0, 0].tick_params(axis="x", rotation=45)
    merged["complaint_type_name"].value_counts().head(10).plot(kind="barh", ax=axes[0, 1], color="coral")
    axes[0, 1].set_title("Top complaint types")
    merged["Neighborhood"].value_counts().head(10).plot(kind="barh", ax=axes[1, 0], color="seagreen")
    axes[1, 0].set_title("Top neighborhoods (city field)")
    merged["status_type_name"].value_counts().plot(kind="bar", ax=axes[1, 1], color=["#2ecc71", "#e74c3c"])
    axes[1, 1].set_title("Open vs closed")
    plt.tight_layout()

    out_reports = os.path.join(REPORTS_FIG, "01_eda_overview.png")
    fig.savefig(out_reports, dpi=120, bbox_inches="tight")
    plt.close()

    out_docs = os.path.join(DOCS_IMG, "01_eda_overview.png")
    shutil.copy2(out_reports, out_docs)
    print("Wrote", out_reports)
    print("Copied to", out_docs, "(README + Pages)")


if __name__ == "__main__":
    main()
