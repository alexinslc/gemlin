"""Every test gets its own Gemlin home, so nothing a test does (or starts) touches your ~/.gemlin."""
import pytest


@pytest.fixture(autouse=True)
def gemlin_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMLIN_HOME", str(tmp_path / "gemlin-home"))
