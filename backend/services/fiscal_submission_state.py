"""Positive local evidence for a first invoice submission, never provider absence.

Only enqueue creates NOT_STARTED. A committed POSSIBLE_SUBMISSION precedes
provider I/O; loss of its response cannot reset it. NOT_SUBMITTED is reserved
for the client's typed proof of authentication failure before its first POST.
Old snapshots without this contract are deliberately unknown.
"""
from collections.abc import Mapping

VERSION = 1
NOT_STARTED = "not_started"
POSSIBLE_SUBMISSION = "possible_submission"
NOT_SUBMITTED = "not_submitted"


def initial_state() -> dict:
    return {"submission_state_version": VERSION, "submission_phase": NOT_STARTED}


def can_submit(snapshot) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    version = snapshot.get("submission_state_version")
    phase = snapshot.get("submission_phase")
    return (
        type(version) is int and version == VERSION
        and isinstance(phase, str) and phase in (NOT_STARTED, NOT_SUBMITTED)
        and snapshot.get("send_started", False) is False
        and snapshot.get("retry_signed_after_not_found", False) is False
    )


def mark_possible(snapshot) -> dict:
    if not can_submit(snapshot):
        raise ValueError("No existe evidencia local de un envio no iniciado.")
    return dict(snapshot, submission_phase=POSSIBLE_SUBMISSION, send_started=True)


def mark_not_submitted(snapshot) -> dict:
    if (not isinstance(snapshot, Mapping)
            or type(snapshot.get("submission_state_version")) is not int
            or snapshot.get("submission_state_version") != VERSION
            or snapshot.get("submission_phase") != POSSIBLE_SUBMISSION
            or snapshot.get("send_started") is not True
            or snapshot.get("retry_signed_after_not_found", False) is not False):
        raise ValueError("La prueba de no envio no corresponde al intento actual.")
    return dict(snapshot, submission_phase=NOT_SUBMITTED, send_started=False)
