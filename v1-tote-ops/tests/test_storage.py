"""Supabase Storage helper tests — Task 11."""
import logging
from unittest.mock import MagicMock, patch

import pytest

from app.storage import StorageError, delete_file, get_signed_url, upload_pdf


def _mock_bucket():
    """Return (mock_storage, mock_bucket) for patching get_storage_client."""
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_storage.from_.return_value = mock_bucket
    return mock_storage, mock_bucket


def test_upload_pdf_returns_correct_storage_path_on_success():
    mock_storage, mock_bucket = _mock_bucket()

    with patch("app.storage.get_storage_client", return_value=mock_storage):
        path = upload_pdf(b"pdf bytes", "supplier-1", "gradeout-1", "test.pdf")

    assert path == "supplier-1/gradeout-1.pdf"
    mock_bucket.upload.assert_called_once()


def test_upload_pdf_raises_StorageError_on_client_failure():
    mock_storage, mock_bucket = _mock_bucket()
    mock_bucket.upload.side_effect = Exception("Network error")

    with patch("app.storage.get_storage_client", return_value=mock_storage):
        with pytest.raises(StorageError) as exc_info:
            upload_pdf(b"pdf bytes", "supplier-1", "gradeout-1", "test.pdf")

    assert exc_info.value.context["operation"] == "upload_pdf"
    assert exc_info.value.context["supplier_id"] == "supplier-1"
    assert exc_info.value.context["filename"] == "test.pdf"


def test_get_signed_url_returns_url_string_on_success():
    mock_storage, mock_bucket = _mock_bucket()
    mock_bucket.create_signed_url.return_value = {"signedURL": "https://signed.example.com/file.pdf"}

    with patch("app.storage.get_storage_client", return_value=mock_storage):
        url = get_signed_url("supplier-1/gradeout-1.pdf")

    assert url == "https://signed.example.com/file.pdf"


def test_delete_file_logs_warning_instead_of_raising_when_file_not_found(caplog):
    mock_storage, mock_bucket = _mock_bucket()
    mock_bucket.remove.side_effect = Exception("Object not found")

    with patch("app.storage.get_storage_client", return_value=mock_storage):
        with caplog.at_level(logging.WARNING, logger="app.storage"):
            delete_file("supplier-1/nonexistent.pdf")  # must not raise

    assert any("delete_file" in record.message for record in caplog.records)
