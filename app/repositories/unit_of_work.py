"""Transaction boundary abstraction for repository-backed use cases."""

from typing import Protocol

from sqlmodel import Session


class UnitOfWork(Protocol):
    def commit(self) -> None: ...


class SqlModelUnitOfWork:
    def __init__(self, session: Session):
        self._session = session

    def commit(self) -> None:
        self._session.commit()
