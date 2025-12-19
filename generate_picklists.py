#!/usr/bin/env python3
"""
generate_picklists.py

Reads `swiggy.csv` from the current directory and generates:
  - ./picklists/{date}_ZONE_{ZONE}_PL{n}.csv  (one CSV per picklist)
  - ./Summary.csv                              (one row per picklist)

Behavior:
  - Sorts rows by cutoff datetime (earliest first) then by priority (lower numeric value = higher priority).
  - Splits fragile items (truthy values in fragile column) and non-fragile items.
  - Creates zone-specific picklists greedily:
       max units per picklist = 2000
       max weight per picklist = 200.0 kg (fragile picklists: 50.0 kg)
  - Automatically maps commonly-named columns (order_id, store_id, sku, order_qty, zone, bin, bin_rank, pod_priority, weight_in_grams, fragile, dt/order_date for cutoff).
  - If you want full-file processing on very large files, consider setting MAX_ROWS=None or using chunking (see comment).
"""
"""
Assumption: Infinite pickers
"""
import os
import pandas as pd
from datetime import datetime

# ================= CONFIG =================
INPUT_CSV = "/kaggle/input/swiggy/picklist_creation_data_for_hackathon_with_order_date.csv"
OUTPUT_DIR = "/kaggle/working/picklists"
SUMMARY_CSV = "/kaggle/working/Summary.csv"

MAX_ROWS = None

PICKLIST_UNIT_CAP = 2000
PICKLIST_WEIGHT_CAP = 200.0   # kg
FRAGILE_WEIGHT_CAP = 50.0     # kg

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================


def find_col(cols_lower, candidates):
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


# ================= DATA LOADING =================
def read_and_normalize(input_path):
    print("Loading:", input_path)
    df = pd.read_csv(input_path, low_memory=True)
    print("Rows loaded:", len(df))

    cols_lower = {c.lower(): c for c in df.columns}

    col_order = find_col(cols_lower, ["order_id", "order"])
    col_store = find_col(cols_lower, ["store_id", "store", "pod"])
    col_sku = find_col(cols_lower, ["sku", "product"])
    col_qty = find_col(cols_lower, ["order_qty", "qty", "quantity"])
    col_zone = find_col(cols_lower, ["zone"])
    col_bin = find_col(cols_lower, ["bin", "location"])
    col_binrank = find_col(cols_lower, ["bin_rank", "rank"])
    col_priority = find_col(cols_lower, ["priority", "pod_priority"])
    col_weight = find_col(cols_lower, ["weight", "weight_in_grams"])
    col_fragile = find_col(cols_lower, ["fragile", "is_fragile"])
    col_cutoff = find_col(cols_lower, ["cutoff", "order_date"])

    work = df.copy()

    # Quantity
    if col_qty is None:
        work["_qty"] = 1
    else:
        work["_qty"] = pd.to_numeric(work[col_qty], errors="coerce").fillna(1).astype(int)

    # Weight (ALWAYS grams → kg)
    if col_weight is None:
        work["_weight"] = 0.0
    else:
        work["_weight"] = pd.to_numeric(work[col_weight], errors="coerce").fillna(0.0) / 1000.0

    # Simple string columns
    work["_zone"] = work[col_zone].astype(str) if col_zone else "UNKNOWN"
    work["_sku"] = work[col_sku].astype(str) if col_sku else "SKU_UNKNOWN"
    work["_order"] = work[col_order].astype(str) if col_order else work.index.astype(str)
    work["_store"] = work[col_store].astype(str) if col_store else "STORE_UNKNOWN"
    work["_bin"] = work[col_bin].astype(str) if col_bin else "BIN_UNKNOWN"
    work["_binrank"] = work[col_binrank].astype(str) if col_binrank else ""

    # Priority (SAFE FIX)
    if col_priority is None:
        work["_priority"] = 9999
    else:
        work["_priority"] = pd.to_numeric(work[col_priority], errors="coerce").fillna(9999).astype(int)

    # Fragile
    if col_fragile is None:
        work["_fragile"] = False
    else:
        s = work[col_fragile].astype(str).str.lower().str.strip()
        work["_fragile"] = s.isin(["1", "true", "yes", "y", "t"])

    # Cutoff
    if col_cutoff is None:
        work["_cutoff"] = pd.Timestamp("2100-01-01")
    else:
        work["_cutoff"] = pd.to_datetime(work[col_cutoff], errors="coerce").fillna(
            pd.Timestamp("2100-01-01")
        )

    return work


# ================= PICKLIST GENERATION =================
def generate_picklists(df):
    df = df.sort_values(by=["_cutoff", "_priority", "_order"])

    fragile_df = df[df["_fragile"]]
    normal_df = df[~df["_fragile"]]

    summary = []
    total_picklists = 0

    def process_zone(group, zone, fragile=False):
        nonlocal total_picklists

        cap_units = PICKLIST_UNIT_CAP
        cap_weight = FRAGILE_WEIGHT_CAP if fragile else PICKLIST_WEIGHT_CAP

        cur_units, cur_weight = 0, 0.0
        items, orders, bins = [], set(), set()
        pl_no = 0

        def flush():
            nonlocal cur_units, cur_weight, items, orders, bins, pl_no, total_picklists
            if not items:
                return
            pl_no += 1
            total_picklists += 1

            fname = f"{datetime.now().date()}_ZONE_{zone}_PL{pl_no}.csv"
            pd.DataFrame(items).to_csv(os.path.join(OUTPUT_DIR, fname), index=False)

            summary.append({
                "picklist_file": fname,
                "zone": zone,
                "picklist_no": pl_no,
                "picklist_type": "fragile" if fragile else "normal",
                "total_units": cur_units,
                "total_weight": cur_weight,
                "distinct_orders": len(orders),
                "distinct_bins": len(bins),
            })

            cur_units, cur_weight = 0, 0.0
            items, orders, bins = [], set(), set()

        for row in group.to_dict("records"):
            remaining = row["_qty"]
            unit_wt = row["_weight"]

            while remaining > 0:
                available_units = cap_units - cur_units
                available_weight = cap_weight - cur_weight

                if available_units <= 0 or available_weight <= 0:
                    flush()
                    continue

                max_by_weight = int(available_weight / unit_wt) if unit_wt > 0 else remaining
                take = min(remaining, available_units, max_by_weight)

                if take <= 0:
                    flush()
                    continue

                items.append({
                    "sku": row["_sku"],
                    "order_id": row["_order"],
                    "store": row["_store"],
                    "bin": row["_bin"],
                    "bin_rank": row["_binrank"],
                    "qty": take,
                    "unit_weight": unit_wt,
                    "fragile": row["_fragile"],
                })

                cur_units += take
                cur_weight += take * unit_wt
                orders.add(row["_order"])
                bins.add(row["_bin"])
                remaining -= take

                assert cur_weight <= cap_weight + 1e-6

        flush()

    for zone, g in normal_df.groupby("_zone"):
        process_zone(g, zone, fragile=False)

    for zone, g in fragile_df.groupby("_zone"):
        process_zone(g, zone, fragile=True)

    pd.DataFrame(summary).to_csv(SUMMARY_CSV, index=False)
    print("Total picklists generated:", total_picklists)


# ================= MAIN =================
def main():
    df = read_and_normalize(INPUT_CSV)
    generate_picklists(df)
    print("Picklists written to:", OUTPUT_DIR)
    print("Summary written to:", SUMMARY_CSV)


if __name__ == "__main__":
    main()
