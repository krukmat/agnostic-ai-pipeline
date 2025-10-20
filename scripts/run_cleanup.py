from __future__ import annotations

import os

from orchestrate import cleanup_artifacts  # type: ignore


def main() -> None:
    flush = os.environ.get("FLUSH", os.environ.get("CLEAN_FLUSH", "0"))
    if flush == "1":
        os.environ["CLEAN_FLUSH"] = "1"
    cleanup_artifacts()


if __name__ == "__main__":
    main()
