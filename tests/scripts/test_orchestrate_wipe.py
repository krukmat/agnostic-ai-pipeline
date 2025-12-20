from pathlib import Path

from scripts import orchestrate as orch


def test_wipe_directory_contents(tmp_path):
    d = tmp_path
    sub = d / "sub"
    sub.mkdir()
    f1 = d / "a.txt"
    f1.write_text("abc", encoding="utf-8")
    f2 = sub / "b.txt"
    f2.write_text("abcd", encoding="utf-8")

    files, size = orch._wipe_directory_contents(d)
    assert files == 2
    assert size == len("abc") + len("abcd")
    # Directory remains but empty
    assert d.exists()
    assert not any(d.iterdir())
