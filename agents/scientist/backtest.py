from engine.backtest import *  # noqa: F401,F403

if __name__ == "__main__":
    from engine.backtest import run_backtest
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--output-dataset-path", default=None)
    parser.add_argument("--mode", choices=["capital", "research"], default="capital")
    args = parser.parse_args()
    run_backtest(strategy=args.strategy, publish=args.publish, output_dataset_path=args.output_dataset_path, mode=args.mode)
