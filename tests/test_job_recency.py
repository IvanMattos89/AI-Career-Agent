"""Regressões para o cálculo de recência de anúncios."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.job_search_service import JobSearchService


@pytest.mark.parametrize("days_ago, expected", [
    (-2, 0),
    (0, 5),
    (15, 5),
    (45, 2),
    (120, 0),
])
def test_recency_date_ranges(days_ago, expected):
    published = datetime.now(timezone.utc) - timedelta(days=days_ago)
    assert JobSearchService._pontuacao_recencia(published.isoformat()) == expected


def test_recency_invalid_or_missing_dates():
    assert JobSearchService._pontuacao_recencia("") == 0
    assert JobSearchService._pontuacao_recencia("not-a-date") == 0


def test_recency_naive_datetime_is_treated_as_utc():
    published = datetime.now(timezone.utc) - timedelta(days=10)
    assert JobSearchService._pontuacao_recencia(published.replace(tzinfo=None).isoformat()) == 5
