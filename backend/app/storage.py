import uuid
from pathlib import Path

from .config import settings


class LocalStorage:
    """Swap for an S3 implementation with the same three methods later."""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def new_key(self) -> str:
        return uuid.uuid4().hex

    def path(self, key: str) -> Path:
        return self.root / key

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)


storage = LocalStorage(settings.upload_dir)
