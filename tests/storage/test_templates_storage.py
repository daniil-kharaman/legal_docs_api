import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import HTTPException

from storage.templates_storage import (
    save_file_in_s3,
    get_file_s3,
    delete_file_s3,
    BUCKET_NAME
)


class TestSaveFileInS3:
    """Tests for the save_file_in_s3 function"""

    @patch('storage.templates_storage.s3_client')
    def test_save_file_success(self, mock_s3_client):
        """Test successful file upload to S3"""
        mock_buffer = BytesIO(b"test file content")
        object_key = "test_file.txt"

        save_file_in_s3(mock_buffer, object_key)

        mock_s3_client.upload_fileobj.assert_called_once_with(
            mock_buffer,
            BUCKET_NAME,
            object_key
        )

    @patch('storage.templates_storage.s3_client')
    def test_save_file_with_nested_path(self, mock_s3_client):
        """Test uploading file with nested path"""
        mock_buffer = BytesIO(b"document content")
        object_key = "templates/user123/document.docx"

        save_file_in_s3(mock_buffer, object_key)

        mock_s3_client.upload_fileobj.assert_called_once_with(
            mock_buffer,
            BUCKET_NAME,
            object_key
        )

    @patch('storage.templates_storage.s3_client')
    def test_save_large_file(self, mock_s3_client):
        """Test uploading large file"""
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        mock_buffer = BytesIO(large_content)
        object_key = "large_file.bin"

        save_file_in_s3(mock_buffer, object_key)

        mock_s3_client.upload_fileobj.assert_called_once()

    @patch('storage.templates_storage.s3_client')
    def test_save_file_s3_error(self, mock_s3_client):
        """Test handling of S3 errors during upload"""
        mock_s3_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "upload_fileobj"
        )

        mock_buffer = BytesIO(b"test content")
        object_key = "test_file.txt"

        with pytest.raises(HTTPException) as exc_info:
            save_file_in_s3(mock_buffer, object_key)

        assert exc_info.value.status_code == 400
        assert "AWS Error" in exc_info.value.detail


class TestGetFileS3:
    """Tests for the get_file_s3 function"""

    @patch('storage.templates_storage.s3_client')
    def test_get_file_success(self, mock_s3_client):
        """Test successful file download from S3"""
        object_key = "test_file.txt"
        expected_content = b"file content from s3"

        def mock_download(bucket, key, buffer):
            buffer.write(expected_content)

        mock_s3_client.download_fileobj.side_effect = mock_download

        result = get_file_s3(object_key)

        assert isinstance(result, BytesIO)
        assert result.read() == expected_content
        mock_s3_client.download_fileobj.assert_called_once()

    @patch('storage.templates_storage.s3_client')
    def test_get_file_with_nested_path(self, mock_s3_client):
        """Test downloading file with nested path"""
        object_key = "templates/user456/template.docx"
        content = b"template content"

        def mock_download(bucket, key, buffer):
            buffer.write(content)

        mock_s3_client.download_fileobj.side_effect = mock_download

        result = get_file_s3(object_key)

        assert result.read() == content

    @patch('storage.templates_storage.s3_client')
    def test_get_file_not_found(self, mock_s3_client):
        """Test handling when file doesn't exist in S3"""
        mock_s3_client.download_fileobj.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}},
            "download_fileobj"
        )

        object_key = "nonexistent.txt"

        with pytest.raises(HTTPException) as exc_info:
            get_file_s3(object_key)

        assert exc_info.value.status_code == 400
        assert "AWS Error" in exc_info.value.detail

    @patch('storage.templates_storage.s3_client')
    def test_get_file_buffer_position(self, mock_s3_client):
        """Test that buffer position is reset to start"""
        object_key = "test.txt"
        content = b"test data"

        def mock_download(bucket, key, buffer):
            buffer.write(content)

        mock_s3_client.download_fileobj.side_effect = mock_download

        result = get_file_s3(object_key)

        # Buffer should be at position 0
        assert result.tell() == 0
        assert result.read() == content

    @patch('storage.templates_storage.s3_client')
    def test_get_empty_file(self, mock_s3_client):
        """Test downloading empty file"""
        object_key = "empty.txt"

        def mock_download(bucket, key, buffer):
            pass  # Don't write anything

        mock_s3_client.download_fileobj.side_effect = mock_download

        result = get_file_s3(object_key)

        assert result.read() == b""


class TestDeleteFileS3:
    """Tests for the delete_file_s3 function"""

    @patch('storage.templates_storage.s3_client')
    def test_delete_file_success(self, mock_s3_client):
        """Test successful file deletion from S3"""
        object_key = "file_to_delete.txt"

        delete_file_s3(object_key)

        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=BUCKET_NAME,
            Key=object_key
        )

    @patch('storage.templates_storage.s3_client')
    def test_delete_file_with_nested_path(self, mock_s3_client):
        """Test deleting file with nested path"""
        object_key = "templates/user789/old_template.docx"

        delete_file_s3(object_key)

        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=BUCKET_NAME,
            Key=object_key
        )

    @patch('storage.templates_storage.s3_client')
    def test_delete_nonexistent_file(self, mock_s3_client):
        """Test deleting file that doesn't exist (S3 returns success anyway)"""
        object_key = "nonexistent_file.txt"
        mock_s3_client.delete_object.return_value = {}

        # S3 delete_object doesn't raise error for non-existent files
        delete_file_s3(object_key)

        mock_s3_client.delete_object.assert_called_once()

    @patch('storage.templates_storage.s3_client')
    def test_delete_file_s3_error(self, mock_s3_client):
        """Test handling of S3 errors during deletion"""
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "delete_object"
        )

        object_key = "protected_file.txt"

        with pytest.raises(HTTPException) as exc_info:
            delete_file_s3(object_key)

        assert exc_info.value.status_code == 400
        assert "AWS Error" in exc_info.value.detail

    @patch('storage.templates_storage.s3_client')
    def test_delete_multiple_files_sequentially(self, mock_s3_client):
        """Test deleting multiple files in sequence"""
        files = ["file1.txt", "file2.txt", "file3.txt"]

        for file in files:
            delete_file_s3(file)

        assert mock_s3_client.delete_object.call_count == 3


class TestS3IntegrationScenarios:
    """Integration-style tests for common S3 workflows"""

    @patch('storage.templates_storage.s3_client')
    def test_save_and_get_file_workflow(self, mock_s3_client):
        """Test uploading and then downloading a file"""
        content = b"workflow test content"
        object_key = "workflow_test.txt"

        # Upload
        upload_buffer = BytesIO(content)
        save_file_in_s3(upload_buffer, object_key)

        # Download
        def mock_download(bucket, key, buffer):
            buffer.write(content)

        mock_s3_client.download_fileobj.side_effect = mock_download
        download_buffer = get_file_s3(object_key)

        assert download_buffer.read() == content

    @patch('storage.templates_storage.s3_client')
    def test_upload_download_delete_workflow(self, mock_s3_client):
        """Test complete lifecycle: upload, download, delete"""
        content = b"lifecycle test"
        object_key = "lifecycle.txt"

        # Upload
        upload_buffer = BytesIO(content)
        save_file_in_s3(upload_buffer, object_key)
        assert mock_s3_client.upload_fileobj.called

        # Download
        def mock_download(bucket, key, buffer):
            buffer.write(content)

        mock_s3_client.download_fileobj.side_effect = mock_download
        download_buffer = get_file_s3(object_key)
        assert download_buffer.read() == content

        # Delete
        delete_file_s3(object_key)
        assert mock_s3_client.delete_object.called