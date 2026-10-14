import logging
import shutil
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentStorage:
    """Keeps uploaded files under `<root>/<user_id>/<document_id>.pdf`.

    Paths stored on the model are relative to the root, so the storage directory can move.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def path_for(user_id: uuid.UUID, document_id: uuid.UUID) -> str:
        return f"{user_id}/{document_id}.pdf"

    def save(self, storage_path: str, data: bytes) -> None:
        destination = self.root / storage_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(f"{destination.name}.part")
        partial.write_bytes(data)
        partial.replace(destination)

    def delete(self, storage_path: str) -> None:
        (self.root / storage_path).unlink(missing_ok=True)

    def delete_user_files(self, user_id: uuid.UUID | str) -> None:
        """Best effort: a failure is logged rather than raised, since it runs after the account is gone."""
        try:
            shutil.rmtree(self.root / str(user_id))
        except FileNotFoundError:
            return
        except OSError:
            logger.exception("Could not remove stored documents of user %s", user_id)
