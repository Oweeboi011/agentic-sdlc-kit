import pytest

from kit_sync import __version__
from kit_sync.cli import main


def test_version_flag_prints_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"kit-sync {__version__}"


def test_render_without_config_reports_it(tmp_path, capsys):
    assert main(["--project", str(tmp_path)]) == 1
    assert ".github/astral-kit.yml: not found" in capsys.readouterr().out
