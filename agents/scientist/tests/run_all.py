from tests import test_parity_v0_v1, test_smoke


def run() -> None:
    test_smoke.test_returns_config_weights_60_40()
    test_smoke.test_no_trades_on_non_rebalance_date()
    test_smoke.test_correct_trades_on_rebalance_date()
    test_parity_v0_v1.test_v0_v1_parity_on_fixture()
    print("test_runner: PASS")


if __name__ == "__main__":
    run()
