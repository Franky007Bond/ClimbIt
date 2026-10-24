import pytest

from app.api.wiki_rate_limit import reset_wiki_anonymous_rate_limit_buckets


def _module_skipif_needs_database_url(module) -> bool:
    mark = getattr(module, "pytestmark", None)
    if mark is None:
        return False
    marks = mark if isinstance(mark, list) else [mark]
    for item in marks:
        if item.name != "skipif":
            continue
        if item.args and "DATABASE_URL" in str(item.args[0]):
            return True
        if "DATABASE_URL" in str(item.kwargs.get("reason", "")):
            return True
    return False


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        module_name = item.module.__name__
        if module_name.endswith("test_openapi_contract"):
            item.add_marker(pytest.mark.contract)
        elif _module_skipif_needs_database_url(item.module):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(autouse=True)
def _isolated_wiki_anonymous_rate_limit() -> None:
    reset_wiki_anonymous_rate_limit_buckets()
