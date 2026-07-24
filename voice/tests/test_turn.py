"""Turn controller tests."""

from forge_voice.turn import TurnController


def test_cancel_turn_marks_abandoned():
    turns = TurnController()
    turn_id = turns.begin_turn()
    assert not turns.is_cancelled(turn_id)
    turns.cancel_turn()
    assert turns.is_cancelled(turn_id)
    assert not turns.is_active(turn_id)


def test_new_turn_invalidates_old():
    turns = TurnController()
    old = turns.begin_turn()
    new = turns.begin_turn()
    assert turns.is_cancelled(old)
    assert turns.is_active(new)
