from __future__ import annotations

from pathlib import Path

FORBIDDEN_ROOT_FILES = {
    "AGENTS.md",
    "BOOTSTRAP.md",
    "IDENTITY.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
    "HEARTBEAT.md",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def assert_root_write_allowed(target: Path) -> None:
    root = repo_root().resolve()
    t = target.resolve()

    if t.parent == root:
        if t.name != "BOOTSTRAP_EXPORT.txt":
            raise RuntimeError("Root write blocked: immutable root policy.")


def assert_not_forbidden_identity_root_file(target: Path) -> None:
    root = repo_root().resolve()
    t = target.resolve()
    if t.parent == root and t.name in FORBIDDEN_ROOT_FILES:
        raise RuntimeError("Root write blocked: immutable root policy.")
