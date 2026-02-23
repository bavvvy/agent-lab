from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hierarchy_loader import load_hierarchy
from weighting_logic import weight_level_one, weight_within_group
from io_guard import assert_not_forbidden_identity_root_file, assert_root_write_allowed


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _collect_allocations(hierarchy: dict) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []

    l1_weights = weight_level_one(hierarchy)

    for l1, l1_node in hierarchy.items():
        w1 = l1_weights.get(str(l1), 0.0)

        l2_weights = weight_within_group(l1_node)
        for l2, l2_node in l1_node.items():
            w2 = l2_weights.get(str(l2), 0.0)

            l3_weights = weight_within_group(l2_node)
            for l3, l3_node in l2_node.items():
                w3 = l3_weights.get(str(l3), 0.0)

                l4_weights = weight_within_group(l3_node)
                for l4, instruments in l3_node.items():
                    w4 = l4_weights.get(str(l4), 0.0)

                    instrument_weights = weight_within_group(instruments)
                    for i, instrument in enumerate(instruments):
                        wi = instrument_weights.get(str(i), 0.0)
                        rows.append(
                            {
                                "level1_asset_class": l1,
                                "level2_sub_asset_class": l2,
                                "level3_strategy_style": l3,
                                "level4_instrument": l4,
                                "instrument_type": instrument["instrument_type"],
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
        df = df.groupby(
            [
                "level1_asset_class",
                "level2_sub_asset_class",
                "level3_strategy_style",
                "level4_instrument",
                "instrument_type",
            ],
            as_index=False,
        )["target_weight"].sum()

    assert_root_write_allowed(out_path)
    assert_not_forbidden_identity_root_file(out_path)
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    path = run_allocator()
    print(path)
