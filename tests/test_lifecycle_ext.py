
from app.models.application import (
    ApplicationAction,
    StateFactory,
)


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
