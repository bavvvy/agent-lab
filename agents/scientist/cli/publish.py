from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.publish import *  # noqa: F401,F403

if __name__ == "__main__":
    from engine.publish import main
    raise SystemExit(main())
