import time

import pytest

from src.core.renamer import TVShowRenamer


@pytest.fixture
def renamer(monkeypatch):
    monkeypatch.setenv("TMDB_API_KEY", "test-key")
    return TVShowRenamer(None)


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("01 - Show Season 2 [1080p][x264].mkv", ("Show Season 2", 2, 1)),
        ("07 - Show Season 3 [1080p.x264].mkv", ("Show Season 3", 3, 7)),
        ("1 - Title Season 1 [tag] more [tag2].ext", ("Title Season 1", 1, 1)),
        ("Show.Name.S01E02.mkv", ("Show Name", 1, 2)),
    ],
)
def test_extract_show_info(renamer, filename, expected):
    assert renamer.extract_show_info(filename) == expected


def test_extract_show_info_rejects_bracket_flood_quickly(renamer):
    start = time.perf_counter()
    assert renamer.extract_show_info("01 - " + "][" * 120) is None
    assert time.perf_counter() - start < 1.0
