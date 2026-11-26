"""Persistence operations for administrator applicant-package export audits."""

from sqlmodel import Session

from app.models.export_audit import ExportAudit


class ExportAuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, audit: ExportAudit) -> ExportAudit:
        self.db.add(audit)
        self.db.flush()
        return audit
