from __future__ import annotations

from bsdgs_verifier.selection_state import SelectionState, SelectionStateManager


def test_selection_state_round_trip(tmp_path):
    path = tmp_path / "selection_state.json"
    manager = SelectionStateManager(path)
    expected = SelectionState(
        selected_bsdg_id="bsdg-litoral",
        scheduled_bsdg_id="bsdg-litoral",
    )

    manager.save(expected)
    loaded = manager.load()

    assert loaded == expected


def test_selection_state_uses_defaults_for_invalid_json(tmp_path):
    path = tmp_path / "selection_state.json"
    path.write_text("{arquivo inválido", encoding="utf-8")

    loaded = SelectionStateManager(path).load()

    assert loaded == SelectionState()
