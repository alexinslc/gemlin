"""Offline tests: no API key or network needed. Run with: python -m pytest"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import gemlin  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A fake home folder, plus fresh skills/trust locations, so tests never touch yours."""
    monkeypatch.setattr(gemlin, "HOME", tmp_path)
    monkeypatch.setattr(gemlin, "REVIEW", tmp_path / "Gemlin_Review")
    monkeypatch.setattr(gemlin, "SKILLS", tmp_path / "skills")
    monkeypatch.setattr(gemlin, "TRUSTED", tmp_path / ".trusted_skills")
    monkeypatch.setattr(gemlin, "TOOLS", list(gemlin.TOOLS))
    monkeypatch.setattr(gemlin, "inbox", gemlin.queue.Queue())
    return tmp_path


def answer(monkeypatch, *lines):
    """Pretend these lines were typed in the terminal."""
    for line in lines:
        gemlin.inbox.put(("you", line))


def test_file_infos_skips_files_that_vanish(home):
    (home / "here.txt").write_text("hi")
    infos = gemlin.file_infos([home / "here.txt", home / "gone.txt"])
    assert [i["path"] for i in infos] == ["~/here.txt"]


def test_scan_downloads_lists_largest_first(home):
    (home / "Downloads").mkdir()
    (home / "Downloads" / "small.txt").write_bytes(b"x" * 10)
    (home / "Downloads" / "big.zip").write_bytes(b"x" * 300_000)
    (home / "Downloads" / ".hidden").write_bytes(b"x" * 900_000)
    result = gemlin.scan_downloads()
    assert result["count"] == 2
    assert result["files"][0]["path"] == "~/Downloads/big.zip"


def test_find_big_files_skips_hidden_folders(home):
    (home / ".cache").mkdir()
    (home / ".cache" / "huge.bin").write_bytes(b"x" * 500_000)
    (home / "video.mp4").write_bytes(b"x" * 200_000)
    assert [f["path"] for f in gemlin.find_big_files(str(home), 5)] == ["~/video.mp4"]


def test_top_processes_cpu_is_share_of_whole_machine():
    rows = gemlin.top_processes(3)
    assert len(rows) <= 3
    assert all(0 <= r["cpu"] <= 100 for r in rows)


def test_quarantine_refuses_outside_home_and_folders(home, tmp_path_factory):
    outside = tmp_path_factory.mktemp("elsewhere") / "file.txt"
    outside.write_text("x")
    (home / "folder").mkdir()
    assert gemlin.quarantine_file(str(outside)).startswith("Refused")
    assert gemlin.quarantine_file(str(home / "folder")).startswith("Refused")
    assert outside.exists()


def test_quarantine_moves_only_after_yes(home, monkeypatch):
    f = home / "old.dmg"
    f.write_text("x")
    answer(monkeypatch, "n")
    assert "untouched" in gemlin.quarantine_file(str(f)) and f.exists()
    answer(monkeypatch, "y")
    gemlin.quarantine_file(str(f))
    assert not f.exists() and (home / "Gemlin_Review" / "old.dmg").exists()


def test_load_skill_needs_matching_function_name():
    with pytest.raises(ValueError):
        gemlin.load_skill("wanted", "def other():\n    return 1\n")


def test_learn_skill_saves_and_trusts_approved_code(home, monkeypatch):
    answer(monkeypatch, "y")
    code = 'def hello() -> str:\n    """Say hi."""\n    return "hi"\n'
    assert gemlin.learn_skill("hello", "says hi", code).startswith("Installed")
    saved = (home / "skills" / "hello.py").read_text(encoding="utf-8")
    assert gemlin.fingerprint(saved) in gemlin.TRUSTED.read_text().split()


def test_learn_skill_declined_writes_nothing(home, monkeypatch):
    answer(monkeypatch, "n")
    gemlin.learn_skill("nope", "x", "def nope():\n    return 1\n")
    assert not (home / "skills").exists()


def test_startup_asks_before_loading_new_or_changed_skills(home, monkeypatch, capsys):
    skills = home / "skills"
    skills.mkdir()
    (skills / "ping.py").write_text('def ping() -> str:\n    """Pong."""\n    return "pong"\n', encoding="utf-8")
    for name in ("read_terminal", "start_pet"):
        monkeypatch.setattr(gemlin, name, lambda: None)
    monkeypatch.setattr(gemlin.genai, "Client", lambda: None)
    monkeypatch.setattr(gemlin, "new_chat", lambda history=None: None)

    def run(*typed):
        answer(monkeypatch, *typed, None)  # None = the terminal closed, which ends the chat
        gemlin.main()
        return capsys.readouterr().out.count("Load this skill")

    assert run("y") == 1  # first run: asks, then trusts it
    assert "ping" in [t.__name__ for t in gemlin.TOOLS]
    assert run() == 0  # same code: no question
    (skills / "ping.py").write_text('def ping() -> str:\n    """Changed."""\n    return "!"\n', encoding="utf-8")
    assert run("n") == 1  # edited file: asks again


def test_pet_messages_wait_while_the_terminal_answers_a_question(home):
    gemlin.inbox.put(("pet", "hello from the pet"))
    gemlin.inbox.put(("you", "y"))
    assert gemlin.next_line("you") == ("you", "y")
    assert gemlin.next_line("you", "pet") == ("pet", "hello from the pet")


def test_look_code_from_the_creator_sets_name_and_personality(home, monkeypatch, capsys):
    monkeypatch.setattr(gemlin.pet, "SETTINGS", home / "gemlin.json")
    for name in ("read_terminal", "start_pet"):
        monkeypatch.setattr(gemlin, name, lambda: None)
    monkeypatch.setattr(gemlin.genai, "Client", lambda: None)
    monkeypatch.setattr(gemlin, "new_chat", lambda history=None: None)
    monkeypatch.setattr(gemlin, "NAME", gemlin.NAME)
    monkeypatch.setattr(gemlin, "PERSONA", gemlin.PERSONA)
    code = gemlin.pet.base64.urlsafe_b64encode(b'{"name": "Pebble", "personality": "a calm rock."}').decode().rstrip("=")
    monkeypatch.setattr(gemlin.sys, "argv", ["gemlin.py", "--look", code])
    answer(monkeypatch, None)
    gemlin.main()
    assert gemlin.NAME == "Pebble" and gemlin.PERSONA == "You are Pebble, a calm rock."
    assert "Pebble wakes up" in capsys.readouterr().out


def test_lines_typed_into_the_pet_reach_the_chat(home):
    class FakePet:
        stdout = ['{"say": "hi from the desktop"}\n', "not json\n", '{"other": 1}\n', '{"say": "again"}\n']
    gemlin.read_pet(FakePet)
    assert gemlin.next_line("pet") == ("pet", "hi from the desktop")
    assert gemlin.next_line("pet") == ("pet", "again")
