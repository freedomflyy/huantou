from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.models import Asset
from app.services.storage import StorageError, delete_object


def main() -> None:
    now = datetime.now(timezone.utc)
    total = 0
    deleted_file = 0
    skipped_file = 0

    with SessionLocal() as db:
        stmt = select(Asset).where(
            Asset.expires_at.is_not(None),
            Asset.expires_at < now,
            Asset.is_removed.is_(False),
        )
        rows = db.scalars(stmt).all()
        for asset in rows:
            total += 1
            try:
                removed = delete_object(
                    storage_provider=asset.storage_provider,
                    object_key=asset.object_key,
                )
                if removed:
                    deleted_file += 1
                else:
                    skipped_file += 1
            except StorageError:
                skipped_file += 1

            asset.is_removed = True
            asset.removed_reason = "expired_cleanup"

        db.commit()

    print(
        {
            "expired_assets_processed": total,
            "underlying_file_deleted": deleted_file,
            "underlying_file_skipped": skipped_file,
        }
    )


if __name__ == "__main__":
    main()
