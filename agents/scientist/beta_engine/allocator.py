from __future__ import annotations

from pathlib import Path

import pandas as pd

from hierarchy_loader import load_hierarchy
from weighting_logic import weight_level_one, weight_within_group


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _collect_allocations(hierarchy: dict) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []

    l1_weights = weight_level_one(hierarchy)

    for l1, l1_node in hierarchy.items():
        w1 = l1_weights.get(l1, 0.0)

        l2_weights = weight_within_group(l1_node)
        for l2, l2_node in l1_node.items():
            w2 = l2_weights.get(l2, 0.0)

            l3_weights = weight_within_group(l2_node)
            for l3, l3_node in l2_node.items():
                w3 = l3_weights.get(l3, 0.0)

                l4_weights = weight_within_group(l3_node)
                for l4, leaf_list in l3_node.items():
                    w4 = l4_weights.get(l4, 0.0)

                    leaf_weights = weight_within_group(leaf_list)
                    for i, leaf in enumerate(leaf_list):
                        wi = leaf_weights.get(str(i), 0.0)
                        rows.append(
                            {
                                "ticker": leaf["ticker"],
                                "instrument_type": leaf["instrument_type"],
                                "target_weight": w1 * w2 * w3 * w4 * wi,
                            }
                        )

    return rows


def run_allocator() -> Path:
    hierarchy = load_hierarchy()
    rows = _collect_allocations(hierarchy)

    out_dir = _repo_root() / "outputs" / "runtime"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "beta_targets.csv"

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.groupby(["ticker", "instrument_type"], as_index=False)["target_weight"].sum()

    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    path = run_allocator()
    print(path)
