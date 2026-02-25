from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.backtest import *  # noqa: F401,F403

if __name__ == "__main__":
    import argparse

    from portfolio_engine.engine import run_portfolio_pipeline

    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--output-dataset-path", default=None)
    parser.add_argument("--mode", choices=["capital", "research"], default="capital")
    args = parser.parse_args()
    run_portfolio_pipeline(
        strategy_name=args.strategy,
        mode=args.mode,
        publish=args.publish,
        output_dataset_path=args.output_dataset_path,
    )
