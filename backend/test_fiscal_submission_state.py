"""Fail-closed boundary for untrusted or historical submission snapshots."""
import pytest
from services import fiscal_submission_state as state


@pytest.mark.parametrize("snapshot", [None, [], {}, {"send_started": False},
    {"sign_only": True}, {"signed_ready": True}])
def test_legacy_or_missing_evidence_never_authorizes_submit(snapshot):
    assert not state.can_submit(snapshot)
    with pytest.raises(ValueError):
        state.mark_possible(snapshot)


@pytest.mark.parametrize("key,value", [
    ("submission_state_version", True), ("submission_state_version", "1"),
    ("submission_state_version", 1.0), ("submission_state_version", 2),
    ("submission_phase", []), ("submission_phase", None),
    ("submission_phase", state.POSSIBLE_SUBMISSION),
    ("send_started", True), ("send_started", None), ("send_started", "false"),
    ("send_started", 0), ("retry_signed_after_not_found", True),
    ("retry_signed_after_not_found", "false"), ("retry_signed_after_not_found", None),
])
def test_malformed_or_conflicting_evidence_is_unknown(key, value):
    assert not state.can_submit(dict(state.initial_state(), **{key: value}))


def test_only_current_started_attempt_can_be_proven_not_submitted():
    initial = state.initial_state()
    possible = state.mark_possible(initial)
    assert state.can_submit(initial)
    assert not state.can_submit(possible)
    safe = state.mark_not_submitted(possible)
    assert state.can_submit(safe)
    assert safe['submission_phase'] == state.NOT_SUBMITTED
    assert state.mark_possible(safe) == possible
    with pytest.raises(ValueError):
        state.mark_not_submitted(initial)
    with pytest.raises(ValueError):
        state.mark_not_submitted({"send_started": True})
    with pytest.raises(ValueError):
        state.mark_not_submitted(dict(possible, retry_signed_after_not_found=True))
