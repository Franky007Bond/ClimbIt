import pytest

from app.api.wiki_rate_limit import reset_wiki_anonymous_rate_limit_buckets


@pytest.fixture(autouse=True)
def _isolated_wiki_anonymous_rate_limit() -> None:
    reset_wiki_anonymous_rate_limit_buckets()
