from __future__ import annotations

# Re-exports to preserve backward compatibility with existing imports
from .cli import main  # re-export for python -m drivers.registry
from .loader import load_driver  # legacy import path support
from .validator import VALID_CATEGORIES  # legacy import path support

if __name__ == "__main__":  # pragma: no cover
    import sys
    from .cli import main as _main
    raise SystemExit(_main(sys.argv[1:]))
