# Swiggy_Hackathon
# 📦 Picklist Generation System

## Overview

This project implements a **scalable, production-grade picklist generation system** for warehouse operations.
It processes a large order-level dataset (1M+ rows) and generates **zone-wise picklists** under operational constraints such as:

* Maximum units per picklist
* Maximum weight per picklist
* Fragile item handling
* Order priority and cutoff deadlines

The solution is optimized for **large datasets** and is suitable for **Kaggle kernels, hackathons, and real-world warehouse planning**.

---

## 🚀 What This Script Does

Given an input CSV (`swiggy.csv`):

1. **Automatically detects column names** (robust to schema variations)
2. **Computes absolute cutoff times** from POD priority
3. **Sorts orders by urgency** (cutoff → priority → order)
4. **Splits data into fragile & non-fragile flows**
5. **Generates picklists zone-wise using a greedy algorithm**
6. **Enforces hard constraints**:

   * Max units per picklist = 2000
   * Max weight = 200 kg (50 kg for fragile)
7. **Outputs**:

   * One CSV per picklist
   * A global `Summary.csv` with picklist metadata

---

## 📁 Output Structure

```
.
├── picklists/
│   ├── 2025-01-15_ZONE_A_PL1.csv
│   ├── 2025-01-15_ZONE_A_PL2.csv
│   ├── 2025-01-15_ZONE_B_PL1.csv
│   └── ...
├── Summary.csv
└── generate_picklists.py
```

### Picklist CSV Columns

Each picklist file contains:

* `sku`
* `order_id`
* `store`
* `bin`
* `bin_rank`
* `qty`
* `unit_weight`
* `cutoff`
* `priority`
* `fragile`

### Summary.csv Columns

* `picklist_file`
* `zone`
* `picklist_no`
* `picklist_type` (fragile / normal)
* `total_units`
* `total_weight`
* `distinct_orders`
* `distinct_bins`
* `earliest_cutoff`
* `created_at`

---

## ⚙️ Configuration

Inside `generate_picklists.py`:

```python
INPUT_CSV = "swiggy.csv"
OUTPUT_DIR = "picklists"
SUMMARY_CSV = "Summary.csv"

PICKLIST_UNIT_CAP = 2000
PICKLIST_WEIGHT_CAP = 200.0
FRAGILE_WEIGHT_CAP = 50.0

MAX_ROWS = None  # Set to an integer for testing
```

---

## 🧠 Algorithm Used

### Greedy EDF Bin-Packing (Heuristic)

* **EDF (Earliest Deadline First)** ordering based on cutoff times
* Single-pass greedy packing per zone
* Separate handling for fragile items
* Each row is processed **at most once**

This avoids NP-hard exact optimization while delivering **near-optimal, fast results**.

---

## ⏱ Time & Space Complexity

| Component           | Complexity     |
| ------------------- | -------------- |
| Sorting             | O(N log N)     |
| Picklist generation | O(N)           |
| File writing        | O(P)           |
| **Overall**         | **O(N log N)** |

* `N` = number of rows
* `P` = number of picklists

Memory usage is linear in `N`.

---

## 🏎 Performance Characteristics

* Handles **1.2M+ rows** without hanging
* Avoids `iterrows()` and repeated DataFrame scans
* Uses efficient Python data structures
* Kaggle-safe and notebook-friendly

---

## ▶️ How to Run

### Local

```bash
python generate_picklists.py
```

### Kaggle

1. Upload `swiggy.csv`
2. Add this script
3. Run the kernel
4. Outputs will appear in `/kaggle/working/`

---

## 🧪 Testing with Fewer Rows

For quick testing:

```python
MAX_ROWS = 200000
```

---

## ❗ Important Notes

* This is a **heuristic solution** (not exact ILP)
* Guarantees constraint satisfaction
* Optimized for **scale and robustness**, not perfect optimality
* Suitable for real-time or batch planning

---

## 🏆 Why This Solution Is Strong

✔ Scales to million-row datasets
✔ Clear constraint modeling
✔ Real-world warehouse logic
✔ Clean outputs
✔ Interview & hackathon ready

---

## 📌 Future Enhancements (Optional)

* Parallel processing per zone
* Picker assignment optimization
* MILP (PuLP) comparison for small subsets
* Real-time rebalancing

---

## 👤 Author Notes

Designed to demonstrate:

* Algorithmic thinking
* Performance optimization
* Practical system design
* Large-scale data handling

---
