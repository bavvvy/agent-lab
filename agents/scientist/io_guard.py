from __future__ import annotations

from pathlib import Path

FORBIDDEN_IDENTITY_STEMS = {
    "AGENTS",
    "BOOTSTRAP",
    "IDENTITY",
    "SOUL",
    "TOOLS",
    "USER",
    "HEARTBEAT",
}

ALLOWED_ROOT_FILE = "BOOTSTRAP_EXPORT.txt"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _stem_upper(name: str) -> str:
    return Path(name).stem.upper()


def _is_forbidden_identity_name(name: str) -> bool:
    upper_name = name.upper()
    if upper_name in FORBIDDEN_IDENTITY_STEMS:
        return True
    if _stem_upper(name) in FORBIDDEN_IDENTITY_STEMS:
        return True
    return False


def assert_root_write_allowed(target: Path) -> None:
    root = repo_root().resolve()
    t = target.resolve()

    if t.parent == root and t.name != ALLOWED_ROOT_FILE:
        raise RuntimeError("Root write blocked: immutable root policy.")


def assert_not_forbidden_identity_root_file(target: Path) -> None:
    root = repo_root().resolve()
    t = target.resolve()

    if t.parent == root and _is_forbidden_identity_name(t.name):
        raise RuntimeError("Root write blocked: immutable root policy.")
