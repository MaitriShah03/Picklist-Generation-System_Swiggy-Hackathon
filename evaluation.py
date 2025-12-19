# ============================================================
# RESEARCH-GRADE EVALUATION FOR PICKLIST GENERATION (CORRECTED)
# ============================================================

import os
import pandas as pd
import numpy as np

SUMMARY_CSV = "Summary.csv"

PICKLIST_UNIT_CAP = 2000
PICKLIST_WEIGHT_CAP = 200.0   # kg
FRAGILE_WEIGHT_CAP = 50.0     # kg


def evaluate_picklists(summary_csv):
    if not os.path.exists(summary_csv):
        print("Summary file not found.")
        return None

    df = pd.read_csv(summary_csv)

    print("\n================ PICKLIST EVALUATION =================")

    # ----------------------------------------------------
    # 0. WEIGHT UNIT SANITY CHECK
    # ----------------------------------------------------
    if df["total_weight"].mean() > 1000:
        print("⚠️  Detected weight values in GRAMS → converting to KG")
        df["total_weight"] = df["total_weight"] / 1000.0

    # ----------------------------------------------------
    # 1. BASIC STATISTICS
    # ----------------------------------------------------
    total_pl = len(df)
    print(f"Total Picklists Generated: {total_pl}")

    avg_units = df["total_units"].mean()
    avg_weight = df["total_weight"].mean()

    print(f"Average Units per Picklist: {avg_units:.2f}")
    print(f"Average Weight per Picklist (RAW): {avg_weight:.2f} kg")

    # ----------------------------------------------------
    # 2. CAP DEFINITIONS
    # ----------------------------------------------------
    def weight_cap(row):
        return FRAGILE_WEIGHT_CAP if row["picklist_type"] == "fragile" else PICKLIST_WEIGHT_CAP

    df["weight_cap"] = df.apply(weight_cap, axis=1)

    # ----------------------------------------------------
    # 3. CONSTRAINT VIOLATIONS (GROUND TRUTH)
    # ----------------------------------------------------
    df["unit_violation"] = df["total_units"] > PICKLIST_UNIT_CAP
    df["weight_violation"] = df["total_weight"] > df["weight_cap"]

    total_violations = int((df["unit_violation"] | df["weight_violation"]).sum())
    violation_rate = (total_violations / total_pl) * 100 if total_pl > 0 else 0.0

    print(f"Constraint Violations (TRUE): {total_violations}")
    print(f"Violation Rate: {violation_rate:.2f}%")

    # ----------------------------------------------------
    # 4. EFFECTIVE (CAPPED) UTILIZATION
    #    Prevents >100% lies
    # ----------------------------------------------------
    df["effective_weight"] = df[["total_weight", "weight_cap"]].min(axis=1)

    df["unit_util_pct"] = (df["total_units"] / PICKLIST_UNIT_CAP) * 100
    df["weight_util_pct"] = (df["effective_weight"] / df["weight_cap"]) * 100

    avg_unit_util = df["unit_util_pct"].mean()
    avg_weight_util = df["weight_util_pct"].mean()

    print(f"Average Unit Utilization: {avg_unit_util:.2f}%")
    print(f"Average Weight Utilization (EFFECTIVE): {avg_weight_util:.2f}%")

    # ----------------------------------------------------
    # 5. FRAGILE VS NORMAL
    # ----------------------------------------------------
    print("\nPicklist Type Distribution:")
    print(df["picklist_type"].value_counts())

    # ----------------------------------------------------
    # 6. ZONE-LEVEL SCALABILITY
    # ----------------------------------------------------
    print("\nZone-wise Picklists:")
    print(df.groupby("zone").size())

    # ----------------------------------------------------
    # 7. CONSOLIDATION METRICS
    # ----------------------------------------------------
    avg_orders = df["distinct_orders"].mean()
    avg_bins = df["distinct_bins"].mean()

    print(f"\nAverage Orders per Picklist: {avg_orders:.2f}")
    print(f"Average Bins per Picklist: {avg_bins:.2f}")

    # ----------------------------------------------------
    # 8. BASELINE COMPARISON
    # ----------------------------------------------------
    baseline_picklists = int(df["distinct_orders"].sum())
    reduction_pct = (
        (baseline_picklists - total_pl) / baseline_picklists * 100
        if baseline_picklists > 0 else 0.0
    )

    print("\nBaseline Comparison:")
    print(f"Naive Baseline Picklists: {baseline_picklists}")
    print(f"Picklist Reduction vs Baseline: {reduction_pct:.2f}%")

    # ----------------------------------------------------
    # 9. DOMINANCE ANALYSIS (IMPORTANT INSIGHT)
    # ----------------------------------------------------
    unit_dominated = (df["unit_violation"] & ~df["weight_violation"]).sum()
    weight_dominated = (df["weight_violation"] & ~df["unit_violation"]).sum()

    print("\nConstraint Dominance:")
    print(f"Unit-dominated violations: {unit_dominated}")
    print(f"Weight-dominated violations: {weight_dominated}")

    # ----------------------------------------------------
    # 10. COMPOSITE PICKLIST QUALITY SCORE (SAFE PQS)
    # ----------------------------------------------------
    unit_eff = np.clip(avg_unit_util / 100.0, 0.0, 1.0)
    weight_eff = np.clip(avg_weight_util / 100.0, 0.0, 1.0)
    order_eff = np.clip(avg_orders / 20.0, 0.0, 1.0)
    correctness = 1.0 - (violation_rate / 100.0)

    PQS = (
        0.4 * unit_eff +
        0.3 * weight_eff +
        0.2 * order_eff +
        0.1 * correctness
    )

    print("\nComposite Picklist Quality Score (PQS – SAFE):")
    print(f"PQS = {PQS:.3f}  (range: 0–1)")

    print("\n======================================================")

    return {
        "total_picklists": total_pl,
        "avg_unit_util": avg_unit_util,
        "avg_weight_util": avg_weight_util,
        "violation_rate": violation_rate,
        "picklist_reduction_pct": reduction_pct,
        "PQS": PQS
    }


# ---------------- RUN EVALUATION ----------------
metrics = evaluate_picklists(SUMMARY_CSV)
