import pytest

from kit_sync import __version__
from kit_sync.cli import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"kit-sync {__version__}"


def test_no_args_says_rendering_is_pending(capsys):
    assert main([]) == 0
    assert "not implemented yet" in capsys.readouterr().out
