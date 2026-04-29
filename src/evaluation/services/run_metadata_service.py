from datetime import datetime, timezone
from typing import Optional


class RunMetadataService:
    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def timestamp_token(cls, now: Optional[datetime] = None) -> str:
        current = now or cls.utc_now()
        return current.strftime("%Y%m%d_%H%M%S")

    @classmethod
    def iso_utc(cls, now: Optional[datetime] = None) -> str:
        current = now or cls.utc_now()
        return current.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def slugify(value: str) -> str:
        return value.lower().replace(" ", "_")

    @classmethod
    def build_run_id(cls, now: Optional[datetime] = None) -> str:
        return f"run_{cls.timestamp_token(now)}"
