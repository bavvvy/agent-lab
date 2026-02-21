from pathlib import Path

from policy import ensure_timestamped_report_name, parse_report_timestamp_utc, report_rows_for_index


def test_timestamped_report_name_rule():
    ensure_timestamped_report_name("2026-02-21_00-17_beta-engine-60-40.html", "beta-engine-60-40")


def test_timestamped_report_name_rejects_invalid():
    try:
        ensure_timestamped_report_name("beta-engine-60-40.html", "beta-engine-60-40")
        assert False, "expected ValueError"
    except ValueError:
        assert True


def test_index_rows_use_filename_timestamp_and_legacy():
    files = [
        Path("2026-02-21_00-18_beta-engine-60-40.html"),
        Path("legacy_report.html"),
        Path("2026-02-21_00-17_beta-engine-60-40.html"),
    ]
    rows = report_rows_for_index(files)
    assert rows[0][0] == "2026-02-21_00-18_beta-engine-60-40.html"
    assert rows[1][0] == "2026-02-21_00-17_beta-engine-60-40.html"
    assert rows[2][3] == "Legacy"


def test_publish_script_contains_required_head_parity_check():
    publish_py = Path(__file__).resolve().parents[1] / "publish.py"
    src = publish_py.read_text(encoding="utf-8")
    assert "enforce_head_parity" in src
    assert "HEAD_MATCH: true" in src


def test_publish_runs_pytest_before_push():
    publish_py = Path(__file__).resolve().parents[1] / "publish.py"
    src = publish_py.read_text(encoding="utf-8")
    assert "-m\", \"pytest\"" in src or "pytest" in src
    assert "run_pytest(workspace)" in src


def test_parse_timestamp_utc():
    dt = parse_report_timestamp_utc("2026-02-21_00-17_beta-engine-60-40.html")
    assert dt is not None
    assert dt.strftime("%Y-%m-%d %H:%M") == "2026-02-21 00:17"
