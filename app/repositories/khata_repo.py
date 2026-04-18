# app/repositories/khata_repo.py
#
# Data-access layer for KhataEntry.
#
# KEY FIX: All ID values cast to str() before DB filters.
# User.id may be uuid.UUID (as_uuid=True) while KhataEntry uses String
# columns — mixing types causes psycopg2 DataError at the DB level.
# NotFoundException raised OUTSIDE try/except so it always propagates cleanly.

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.khata_entry import KhataEntry
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException


class KhataRepository:
    """
    Repository for KhataEntry persistence operations.

    Args:
        db (Session): SQLAlchemy session injected via FastAPI Depends.
    """

    def __init__(self, db: Session):
        self.db = db

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _safe_query(self, operation_name: str, query_fn):
        """
        Execute a query callable, roll back and raise AppException on failure.

        Rolling back on every SQLAlchemyError ensures the session is never
        left in a broken/unusable state for subsequent requests.

        Args:
            operation_name (str): Label used in log messages.
            query_fn (callable):  Zero-argument callable that runs the query.

        Returns:
            Any: Whatever query_fn returns.

        Raises:
            AppException: 500 on any SQLAlchemyError.
        """
        try:
            return query_fn()
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.error(
                "DB error [%s]: %s",
                operation_name,
                repr(exc),      # repr() shows full class + message
                exc_info=True,
            )
            raise AppException(500, f"Database error during {operation_name}")

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE
    # ─────────────────────────────────────────────────────────────────────────

    def create_entry(self, entry: KhataEntry) -> KhataEntry:
        """
        Persist a new KhataEntry to the database.

        Args:
            entry (KhataEntry): Fully populated ORM object (id already set).

        Returns:
            KhataEntry: Refreshed, persisted entry.

        Raises:
            AppException: 500 on database failure.
        """
        def _run():
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            return entry

        created = self._safe_query("create_entry", _run)
        logger.info(
            "KhataEntry created | id=%s user_id=%s customer=%s total_bill=%s",
            created.id, created.user_id, created.customer_name, created.total_bill,
        )
        return created

    # ─────────────────────────────────────────────────────────────────────────
    # GET ONE
    # ─────────────────────────────────────────────────────────────────────────

    def get_entry(self, entry_id: str, user_id: str) -> KhataEntry:
        """
        Fetch a single KhataEntry scoped to the owning user.

        Security: user_id filter prevents cross-user data access.
        Both IDs cast to str() — safe when User.id is uuid.UUID object.

        Args:
            entry_id (str): UUID of the KhataEntry.
            user_id  (str): UUID of the authenticated user (from JWT).

        Returns:
            KhataEntry: The matched entry.

        Raises:
            AppException:      500 on database failure.
            NotFoundException: if no entry matches (entry_id + user_id).
        """
        # Query inside safe wrapper
        entry = self._safe_query(
            "get_entry",
            lambda: (
                self.db.query(KhataEntry)
                .filter(
                    KhataEntry.id      == str(entry_id),  # str() type safety
                    KhataEntry.user_id == str(user_id),   # str() type safety
                )
                .first()
            ),
        )

        # Not-found check OUTSIDE try/except — propagates cleanly to service
        if entry is None:
            logger.warning(
                "KhataEntry not found | entry_id=%s user_id=%s",
                entry_id, user_id,
            )
            raise NotFoundException(f"Khata entry not found: {entry_id}")

        logger.debug("KhataEntry fetched | id=%s user_id=%s", entry.id, entry.user_id)
        return entry

    # ─────────────────────────────────────────────────────────────────────────
    # GET ALL
    # ─────────────────────────────────────────────────────────────────────────

    def get_all_entries(self, user_id: str) -> list[KhataEntry]:
        """
        Return all KhataEntry rows for a user, newest first.

        Args:
            user_id (str): UUID of the authenticated user.

        Returns:
            list[KhataEntry]: Possibly empty list.

        Raises:
            AppException: 500 on database failure.
        """
        entries = self._safe_query(
            "get_all_entries",
            lambda: (
                self.db.query(KhataEntry)
                .filter(KhataEntry.user_id == str(user_id))  # str() type safety
                .order_by(KhataEntry.created_at.desc())
                .all()
            ),
        )
        logger.debug(
            "KhataEntry list fetched | user_id=%s count=%d",
            user_id, len(entries),
        )
        return entries

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE
    # ─────────────────────────────────────────────────────────────────────────

    def save(self, entry: KhataEntry) -> KhataEntry:
        """
        Commit pending changes on an already-tracked ORM object.

        Args:
            entry (KhataEntry): Dirty ORM object in session identity map.

        Returns:
            KhataEntry: Refreshed entry after commit.

        Raises:
            AppException: 500 on database failure.
        """
        def _run():
            self.db.commit()
            self.db.refresh(entry)
            return entry

        saved = self._safe_query("save", _run)
        logger.debug("KhataEntry saved | id=%s", saved.id)
        return saved

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE
    # ─────────────────────────────────────────────────────────────────────────

    def update_entry(self, entry: KhataEntry, data: dict) -> KhataEntry:
        """
        Apply a partial field dict to an entry and commit.

        Only keys that exist on KhataEntry with non-None values are applied.

        Args:
            entry (KhataEntry): Entry to mutate (already loaded from DB).
            data  (dict):       Partial field map e.g. {"customer_name": "Ali"}.

        Returns:
            KhataEntry: Refreshed entry after commit.

        Raises:
            AppException: 500 on database failure.
        """
        for key, value in data.items():
            if hasattr(entry, key) and value is not None:
                setattr(entry, key, value)

        def _run():
            self.db.commit()
            self.db.refresh(entry)
            return entry

        updated = self._safe_query("update_entry", _run)
        logger.info(
            "KhataEntry updated | id=%s fields=%s",
            updated.id, list(data.keys()),
        )
        return updated

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────────────────────────────────

    def delete_entry(self, entry: KhataEntry) -> bool:
        """
        Hard-delete a KhataEntry. Caller must verify is_cleared first.

        Args:
            entry (KhataEntry): Entry to delete (already loaded from DB).

        Returns:
            bool: True on success.

        Raises:
            AppException: 500 on database failure.
        """
        entry_id = entry.id  # capture before SQLAlchemy clears post-delete

        def _run():
            self.db.delete(entry)
            self.db.commit()
            return True

        result = self._safe_query("delete_entry", _run)
        logger.info("KhataEntry deleted | id=%s", entry_id)
        return result