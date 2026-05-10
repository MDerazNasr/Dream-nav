import sys

from app.command_runner import CommandRunner


def test_command_runner_captures_success_output() -> None:
    result = CommandRunner().run([sys.executable, "-c", "print('poses ready')"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "poses ready"
    assert result.stderr == ""
    assert result.timed_out is False


def test_command_runner_records_failed_exit() -> None:
    result = CommandRunner().run(
        [sys.executable, "-c", "import sys; print('bad poses', file=sys.stderr); sys.exit(7)"]
    )

    assert result.exit_code == 7
    assert result.stderr.strip() == "bad poses"
    assert result.timed_out is False


def test_command_runner_reports_timeout() -> None:
    result = CommandRunner().run(
        [sys.executable, "-c", "import time; time.sleep(1)"],
        timeout_sec=0.01,
    )

    assert result.exit_code is None
    assert result.timed_out is True


def test_command_runner_rejects_shell_strings() -> None:
    try:
        CommandRunner().run("echo unsafe")  # type: ignore[arg-type]
    except TypeError as error:
        assert "argv sequence" in str(error)
    else:
        raise AssertionError("Shell string command was accepted")
