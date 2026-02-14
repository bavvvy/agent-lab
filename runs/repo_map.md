# Repository Map

Generated: 2026-02-14 (Australia/Brisbane)

## Top-level structure

- `AGENTS.md` — workspace operating guide (session startup, memory policy, safety boundaries, heartbeat behavior)
- `SOUL.md` — assistant tone/personality guidance
- `USER.md` — user profile template
- `IDENTITY.md` — assistant identity template
- `TOOLS.md` — local environment/tooling notes template
- `HEARTBEAT.md` — heartbeat task checklist (currently comments only)
- `BOOTSTRAP.md` — first-run onboarding instructions
- `.gitignore` — basic ignore rules
- `venv/` — Python virtual environment (interpreter, pip, site-packages)
- `.git/` — git metadata

## Directory map (concise)

```text
.
├── .git/
├── .gitignore
├── AGENTS.md
├── BOOTSTRAP.md
├── HEARTBEAT.md
├── IDENTITY.md
├── SOUL.md
├── TOOLS.md
├── USER.md
└── venv/
    ├── bin/
    ├── include/
    ├── lib/python3.12/site-packages/
    ├── lib64
    └── pyvenv.cfg
```

## Observations

- This repository is currently **documentation-first** and oriented around assistant behavior/configuration.
- No application source tree (e.g., `src/`, `scripts/`, or tests) is present yet.
- A local virtual environment is tracked in the workspace tree (not necessarily committed, but present locally).

## Suggested improvement (one)

Add a root-level `README.md` that explains:

1. the purpose of this repo,
2. expected directory conventions (`memory/`, `runs/`, optional `scripts/`), and
3. a quick start flow (bootstrap, identity/user setup, and routine maintenance).

This would make onboarding faster and reduce ambiguity for both humans and agents.
