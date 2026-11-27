
import pytest

from app.models.application import (
    ApplicationAction,
    StateFactory,
)
from app.services.lifecycle import ReopenPolicy, apply_action


def test_submitted_state_only_allows_review():
    state = StateFactory.from_status("submitted")

    assert state.allowed_actions() == frozenset({
        ApplicationAction.MARK_REVIEWED
    })


def test_reviewed_state_allows_shortlist_or_reject():
    state = StateFactory.from_status("reviewed")

    assert state.allowed_actions() == frozenset({
        ApplicationAction.SHORTLIST,
        ApplicationAction.REJECT,
    })


def test_shortlisted_state_allows_hire_or_reject():
    state = StateFactory.from_status("shortlisted")

    assert state.allowed_actions() == frozenset({
        ApplicationAction.HIRE,
        ApplicationAction.REJECT,
    })


def test_rejected_state_only_allows_reopen():
    state = StateFactory.from_status("rejected")

    assert state.allowed_actions() == frozenset({
        ApplicationAction.REOPEN
    })


def test_hired_state_has_no_allowed_actions():
    state = StateFactory.from_status("hired")

    assert state.allowed_actions() == frozenset()


def test_apply_action_returns_snapshot_without_mutating_input():
    application = {"id": 5, "status": "submitted", "cover_letter": "private"}

    result = apply_action(application, "mark_reviewed")

    assert result == {
        "ok": True,
        "application": {"id": 5, "status": "reviewed"},
        "row": {
            "id": 5,
            "status": "reviewed",
            "cover_letter": "private",
        },
        "changed": True,
    }
    assert application["status"] == "submitted"


@pytest.mark.parametrize(
    ("application", "action"),
    [
        ({"id": 5, "status": "submitted"}, "shortlist"),
        ({"id": 5, "status": "submitted"}, "invalid"),
        ({"id": 5, "status": "unknown"}, "mark_reviewed"),
    ],
)
def test_apply_action_returns_errors_without_changing_input(application, action):
    result = apply_action(application, action)

    assert result["ok"] is False
    assert "error" in result
    assert application["status"] != "reviewed"


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        ({"role": "admin"}, True),
        ({"role": "employer"}, False),
        ({}, False),
    ],
)
def test_reopen_policy_is_admin_only(actor, expected):
    assert ReopenPolicy.can_reopen(actor) is expected
