"""Persistence operations for applications and their lifecycle history."""

from sqlmodel import Session, select

from app.models.application import Application, ApplicationHistory


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, application_id: int) -> Application | None:
        return self.db.get(Application, application_id)

    def find_for_applicant_and_listing(
        self, graduate_id: int, listing_id: int
    ) -> Application | None:
        return self.db.exec(
            select(Application).where(
                Application.graduate_id == graduate_id,
                Application.listing_id == listing_id,
            )
        ).first()

    def for_applicant(self, graduate_id: int) -> list[Application]:
        return self.db.exec(
            select(Application)
            .where(Application.graduate_id == graduate_id)
            .order_by(Application.id)
        ).all()

    def for_listing(self, listing_id: int) -> list[Application]:
        return self.db.exec(
            select(Application)
            .where(Application.listing_id == listing_id)
            .order_by(Application.id)
        ).all()

    def save(self, application: Application) -> Application:
        self.db.add(application)
        self.db.flush()
        return application

    def add_history(self, history: ApplicationHistory) -> ApplicationHistory:
        self.db.add(history)
        self.db.flush()
        return history
