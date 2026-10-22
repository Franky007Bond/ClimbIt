import os
import subprocess


def main() -> int:
    completed = subprocess.run(["alembic", "upgrade", "head"], check=False)
    if completed.returncode != 0:
        return completed.returncode
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--no-access-log",
        ],
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
