"""Every built-in skill loads, follows the skill rules, and runs on this machine."""
import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from gemlin import core, paths  # noqa: E402

BUILTINS = sorted(paths.BUILTIN_SKILLS.glob("*.py"))


@pytest.mark.parametrize("path", BUILTINS, ids=lambda p: p.stem)
def test_builtin_skill_runs_and_returns_something_small(path, monkeypatch):
    monkeypatch.setattr(core, "TOOLS", [])
    fn = core.load_skill(path.stem, path.read_text(encoding="utf-8"), str(path))
    assert fn.__doc__ and "Use this" in fn.__doc__  # the docstring tells Gemlin when to use it
    result = fn()
    assert isinstance(result, (dict, list))
    assert len(json.dumps(result, default=str)) < 6000  # small enough to send to the model


@pytest.mark.parametrize("path", BUILTINS, ids=lambda p: p.stem)
def test_builtin_skills_only_use_the_standard_library_and_psutil(path):
    allowed = set(sys.stdlib_module_names) | {"psutil"}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in allowed for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module.split(".")[0] in allowed


def test_no_builtin_skill_shadows_a_core_tool():
    assert not {p.stem for p in BUILTINS} & {t.__name__ for t in core.TOOLS}
