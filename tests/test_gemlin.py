"""Offline tests: no API key or network needed. Run with: python -m pytest"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from gemlin import cli, core as gemlin, paths  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A fake home folder, plus fresh skills/trust locations, so tests never touch yours."""
    monkeypatch.setattr(gemlin, "HOME", tmp_path)
    monkeypatch.setattr(gemlin, "REVIEW", tmp_path / "Gemlin_Review")
    monkeypatch.setattr(gemlin, "SKILLS", tmp_path / "skills")
    monkeypatch.setattr(gemlin, "TRUSTED", tmp_path / ".trusted_skills")
    for name in ("HOME", "CONFIG", "LOOK", "SKILLS", "TRUSTED", "LOG", "PID"):  # ~/.gemlin -> a temp folder
        monkeypatch.setattr(paths, name, tmp_path / ".gemlin" / getattr(paths, name).name)
    monkeypatch.setattr(gemlin.pet, "SETTINGS", paths.LOOK)
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
    monkeypatch.setattr(gemlin, "read_terminal", lambda: None)
    monkeypatch.setattr(gemlin.genai, "Client", lambda **kw: None)
    monkeypatch.setattr(gemlin, "new_chat", lambda history=None: None)

    base = list(gemlin.TOOLS)

    def run(*typed):
        monkeypatch.setattr(gemlin, "TOOLS", list(base))  # a fresh start each time, like a real launch
        answer(monkeypatch, *typed, None)  # None = the terminal closed, which ends the chat
        gemlin.main(desktop=False)
        return capsys.readouterr().out.count("Load the skill")

    assert run("y") == 1  # first run: asks, then trusts it
    assert "ping" in [t.__name__ for t in gemlin.TOOLS]
    assert "battery_status" in [t.__name__ for t in gemlin.TOOLS]  # built-in skills never ask
    assert run() == 0  # same code: no question
    (skills / "ping.py").write_text('def ping() -> str:\n    """Changed."""\n    return "!"\n', encoding="utf-8")
    assert run("n") == 1  # edited file: asks again


def test_pet_messages_wait_while_the_terminal_answers_a_question(home):
    gemlin.inbox.put(("pet", "hello from the pet"))
    gemlin.inbox.put(("you", "y"))
    assert gemlin.next_line("you") == ("you", "y")
    assert gemlin.next_line("you", "pet") == ("pet", "hello from the pet")


def test_look_code_from_the_creator_sets_name_and_personality(home, monkeypatch, capsys):
    monkeypatch.setattr(gemlin, "read_terminal", lambda: None)
    monkeypatch.setattr(gemlin.genai, "Client", lambda **kw: None)
    monkeypatch.setattr(gemlin, "new_chat", lambda history=None: None)
    monkeypatch.setattr(gemlin, "NAME", gemlin.NAME)
    monkeypatch.setattr(gemlin, "PERSONA", gemlin.PERSONA)
    code = gemlin.pet.base64.urlsafe_b64encode(b'{"name": "Pebble", "personality": "a calm rock."}').decode().rstrip("=")
    assert cli.main(["look", code]) == 0
    assert "Meet Pebble" in capsys.readouterr().out
    answer(monkeypatch, None)
    gemlin.main(desktop=False)
    assert gemlin.NAME == "Pebble" and gemlin.PERSONA == "You are Pebble, a calm rock."
    assert "Pebble wakes up" in capsys.readouterr().out

def test_lines_typed_into_the_pet_reach_the_chat(home):
    class FakePet:
        stdout = ['{"say": "hi from the desktop"}\n', "not json\n", '{"other": 1}\n', '{"say": "again"}\n',
                  '{"answer": 3, "yes": true}\n', '{"quit": true}\n']
    gemlin.read_pet(FakePet)
    assert gemlin.next_line("pet") == ("pet", "hi from the desktop")
    assert gemlin.next_line("pet") == ("pet", "again")
    assert gemlin.next_line("answer") == ("answer", (3, True))
    assert gemlin.next_line("pet") == ("pet", "quit")  # Go to sleep ends the chat
    assert gemlin.next_line("gone") == ("gone", None)  # and then the pet is gone


def test_questions_can_be_answered_in_the_pet(home, monkeypatch):
    sent = []
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: sent.append(event))
    gemlin.inbox.put(("answer", (gemlin.asked + 1, True)))
    assert gemlin.ask("OK?", code="print(1)") is True
    assert sent[0]["do"] == "ask" and sent[0]["code"] == "print(1)"
    assert sent[-1] == {"do": "answered", "id": gemlin.asked}


def test_a_late_answer_to_an_old_question_is_ignored(home, monkeypatch):
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: None)
    gemlin.inbox.put(("answer", (gemlin.asked, True)))  # left over from the previous question
    gemlin.inbox.put(("answer", (gemlin.asked + 1, False)))
    assert gemlin.ask("Move it?") is False


def test_closed_terminal_waits_for_the_pet_instead_of_saying_no(home, monkeypatch):
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: None)
    monkeypatch.setattr(gemlin, "pet_alive", lambda: True)
    gemlin.inbox.put(("you", None))
    gemlin.inbox.put(("answer", (gemlin.asked + 1, True)))
    assert gemlin.ask("Install it?") is True


def test_setup_saves_a_working_key_privately(home, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "check_key", lambda key: None)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "  my-key  ")
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    cli.main(["setup"])
    assert paths.api_key() == "my-key"
    if sys.platform != "win32":
        assert paths.CONFIG.stat().st_mode & 0o077 == 0  # only you can read it


def test_environment_key_wins_over_the_saved_one(home, monkeypatch):
    cli.save_key("saved-key")
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    assert paths.api_key() == "env-key"


def test_start_needs_a_key(home, monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert cli.main(["start"]) == 1
    assert "gemlin setup" in capsys.readouterr().out


def test_stop_and_status_when_asleep(home, capsys):
    paths.HOME.mkdir(parents=True)
    paths.PID.write_text("999999999")  # a stale pid from a crash
    assert cli.main(["stop"]) == 0 and not paths.PID.exists()
    cli.main(["status"])
    assert "asleep" in capsys.readouterr().out


def test_skills_new_starts_a_skill_that_still_asks_first(home, capsys):
    assert cli.main(["skills", "new", "wifi_name"]) == 0
    assert (paths.SKILLS / "wifi_name.py").exists()
    assert cli.main(["skills", "new", "battery_status"]) == 1  # taken by a built-in
    capsys.readouterr()
    cli.main(["skills"])
    out = capsys.readouterr().out
    assert "battery_status" in out and "wifi_name" in out and "[asks before loading]" in out


def test_going_to_sleep_during_a_question_says_no_and_quits(home, monkeypatch):
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: None)
    gemlin.inbox.put(("pet", "can you hurry?"))  # chat while the question is open: kept for later
    gemlin.inbox.put(("pet", "quit"))
    assert gemlin.ask("Install it?") is False
    assert gemlin.next_line("pet") == ("pet", "can you hurry?")
    assert gemlin.next_line("pet") == ("pet", "quit")  # the main loop still sees it and stops


def test_pet_crash_during_a_question_with_no_terminal_says_no(home, monkeypatch):
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: None)
    monkeypatch.setattr(gemlin, "terminal_open", False)
    gemlin.inbox.put(("gone", None))
    assert gemlin.ask("Move it?") is False
    assert gemlin.next_line("gone") == ("gone", None)


def test_pet_crash_during_a_question_lets_the_terminal_answer(home, monkeypatch):
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: None)
    monkeypatch.setattr(gemlin, "terminal_open", True)
    gemlin.inbox.put(("gone", None))
    gemlin.inbox.put(("you", "y"))
    assert gemlin.ask("Move it?") is True
    assert gemlin.next_line("gone") == ("gone", None)


def test_chat_ends_when_the_terminal_closed_and_then_the_pet_goes(home, monkeypatch, capsys):
    monkeypatch.setattr(gemlin, "read_terminal", lambda: None)
    monkeypatch.setattr(gemlin.genai, "Client", lambda **kw: None)
    monkeypatch.setattr(gemlin, "new_chat", lambda history=None: None)
    monkeypatch.setattr(gemlin, "tell_pet", lambda **event: None)
    monkeypatch.setattr(gemlin, "pet_alive", lambda: True)  # still open when the terminal closes
    gemlin.inbox.put(("you", None))  # the terminal closes first...
    gemlin.inbox.put(("gone", None))  # ...then the pet crashes: nothing left, so Gemlin stops
    gemlin.main(desktop=False)
    assert "goes back to sleep" in capsys.readouterr().out
