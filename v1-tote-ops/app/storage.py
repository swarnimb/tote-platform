import logging

from app.config import settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised on Supabase Storage failures. Carries operation context."""

    def __init__(self, message: str, context: dict | None = None):
        self.context = context or {}
        super().__init__(f"{message} | {self.context}")


def get_storage_client():
    """Initialize and return the Supabase Storage client.

    Lazy import prevents supabase from loading in test contexts that mock this function.
    """
    from supabase import create_client

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY).storage


def upload_pdf(
    file_bytes: bytes,
    supplier_id: str,
    gradeout_id: str,
    filename: str,
) -> str:
    """Upload a gradeout PDF to Supabase Storage.

    Path: {bucket}/{supplier_id}/{gradeout_id}.pdf
    Returns the storage path. Raises StorageError with context on any failure.
    """
    storage_path = f"{supplier_id}/{gradeout_id}.pdf"
    try:
        get_storage_client().from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"},
        )
    except Exception as exc:
        raise StorageError(
            "upload_pdf failed",
            context={
                "operation": "upload_pdf",
                "supplier_id": supplier_id,
                "filename": filename,
            },
        ) from exc
    return storage_path


def get_signed_url(
    storage_path: str,
    expires_in_seconds: int = settings.PDF_SIGNED_URL_EXPIRY_SECONDS,
) -> str:
    """Generate a temporary signed URL for a stored PDF.

    Raises StorageError if the path is not found or the request fails.
    """
    try:
        result = (
            get_storage_client()
            .from_(settings.SUPABASE_STORAGE_BUCKET)
            .create_signed_url(path=storage_path, expires_in=expires_in_seconds)
        )
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            url = result.get("signedURL") or result.get("signedUrl")
            if url:
                return url
        raise ValueError(f"No signed URL in response: {result!r}")
    except StorageError:
        raise
    except Exception as exc:
        raise StorageError(
            "get_signed_url failed",
            context={"operation": "get_signed_url", "storage_path": storage_path},
        ) from exc


def delete_file(storage_path: str) -> None:
    """Delete a file from Supabase Storage.

    Logs a warning on failure — does not raise. Idempotent: safe to call on
    already-deleted or missing paths.
    """
    try:
        get_storage_client().from_(settings.SUPABASE_STORAGE_BUCKET).remove([storage_path])
    except Exception as exc:
        logger.warning(
            "delete_file: failed for %s — %s",
            storage_path,
            str(exc),
            extra={"storage_path": storage_path},
        )
