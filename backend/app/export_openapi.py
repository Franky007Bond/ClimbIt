from __future__ import annotations

import json
from pathlib import Path

from app.main import app

_CONTRACT_RELATIVE = Path("contracts") / "openapi.json"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def contract_path() -> Path:
    return repo_root() / _CONTRACT_RELATIVE


def openapi_document() -> dict:
    document = app.openapi()
    document.setdefault("servers", [{"url": "/"}])
    document.setdefault("security", [])
    return document


def write_openapi(path: Path | None = None) -> Path:
    destination = path or contract_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = openapi_document()
    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False)
    destination.write_text(f"{payload}\n", encoding="utf-8")
    return destination


def main() -> None:
    written = write_openapi()
    print(written)


if __name__ == "__main__":
    main()
