from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import delete

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.db.session import SessionLocal
from app.models import RefreshToken


def main() -> None:
    now = datetime.now(UTC)
    # Keep a short grace window for troubleshooting revoked/expired tokens.
    expire_before = now - timedelta(days=3)

    with SessionLocal() as db:
        stmt = delete(RefreshToken).where(RefreshToken.expires_at < expire_before)
        result = db.execute(stmt)
        db.commit()
        print(
            {
                "deleted_refresh_tokens": int(result.rowcount or 0),
                "expire_before": expire_before.isoformat(),
            }
        )


if __name__ == "__main__":
    main()
