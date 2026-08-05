from __future__ import annotations

from bsdgs_verifier.scheduler import WindowsScheduler


def test_task_command_targets_selected_bsdg():
    command = WindowsScheduler()._task_run_command("bsdg-litoral")

    assert "--scan-all-silent" in command
    assert "--scan-bsdg" in command
    assert "bsdg-litoral" in command


def test_task_command_keeps_all_enabled_mode_without_selection():
    command = WindowsScheduler()._task_run_command()

    assert "--scan-all-silent" in command
    assert "--scan-bsdg" not in command
