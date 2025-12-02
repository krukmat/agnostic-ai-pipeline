from scripts import run_dev


def test_try_recover_commented_yaml():
    text = "# - id: S1\n#   status: todo\n"
    recovered = run_dev._try_recover_commented_yaml(text)
    assert isinstance(recovered, list)
    assert recovered[0]["id"] == "S1"
