from __future__ import annotations

import sys
from pathlib import Path

backend_directory = Path(__file__).resolve().parent / "backend"
if str(backend_directory) not in sys.path:
    sys.path.insert(0, str(backend_directory))

from app.main import app  # noqa: E402

__all__ = ["app"]
