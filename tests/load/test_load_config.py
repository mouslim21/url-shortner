import importlib.util
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

spec = importlib.util.spec_from_file_location(
    "load_runner", Path(__file__).with_name("run.py")
)
load = importlib.util.module_from_spec(spec)
spec.loader.exec_module(load)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--concurrency", "100"],
        ["--duration", "0"],
        ["--rate", "100"],
        ["--create-count", "100"],
        ["--base-url", "https://user:password@example.com"],
        ["--base-url", "https://example.com/?token=secret"],
    ],
)
def test_unsafe_configuration_is_rejected(arguments):
    with pytest.raises(SystemExit):
        load.parse_args(arguments)


def test_dry_run_does_not_make_requests(monkeypatch, capsys):
    opener = Mock()
    monkeypatch.setattr(load, "build_opener", opener)
    load.main(["--dry-run", "--code", "abc1234"])
    opener.assert_not_called()
    assert '"new_records": 0' in capsys.readouterr().out


def test_redirect_is_counted_without_following():
    opener = Mock()
    opener.open.side_effect = HTTPError("http://local/r/code", 302, "Found", {}, None)
    assert load.request(opener, "http://local/r/code")[0] == 302
    assert (
        load.NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere")
        is None
    )
