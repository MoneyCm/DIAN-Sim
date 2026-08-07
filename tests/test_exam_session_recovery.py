from core import session_recovery


def test_recover_question_ids_preserves_order_and_clamps_position():
    ids, position = session_recovery.recover_question_ids(
        ["q1", "removed", "q2"], {"q1", "q2"}, 2
    )
    assert ids == ["q1", "q2"]
    assert position == 1


def test_recover_question_ids_handles_empty_bank():
    assert session_recovery.recover_question_ids(["removed"], set(), 0) == ([], 0)
