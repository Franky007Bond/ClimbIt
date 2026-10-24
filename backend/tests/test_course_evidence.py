from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_course_evidence_and_readme_links() -> None:
    course = REPO_ROOT / "_docs" / "course-evidence.md"
    index = REPO_ROOT / "_docs" / "evidence" / "README.md"
    readme = REPO_ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert course.is_file()
    assert index.is_file()
    assert "AGENTS.MD" in text
    assert "github.com" in text.lower() or "Issues" in text
    assert "deploy-rollback" in text
