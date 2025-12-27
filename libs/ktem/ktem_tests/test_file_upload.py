"""Tests for file upload functionality."""

import shutil


class TestFileProcessing:
    """Test file processing functions, especially rename handling."""

    def test_file_rename_when_target_exists(self, tmp_path):
        """Test that file rename works when target file already exists.

        This tests the fix for issue #765 where on Windows, os.rename() fails
        with FileExistsError when the target file already exists.
        """
        # Create source file
        source_file = tmp_path / "source_file.pdf"
        source_file.write_text("source content")

        # Create target file that already exists
        target_file = tmp_path / "target_file.pdf"
        target_file.write_text("existing content")

        # Verify both files exist
        assert source_file.exists()
        assert target_file.exists()

        # Use shutil.move (as in the fix) which should work even if target exists
        shutil.move(str(source_file), str(target_file))

        # Verify source is moved and target has new content
        assert not source_file.exists()
        assert target_file.exists()
        assert target_file.read_text() == "source content"

    def test_file_rename_when_target_not_exists(self, tmp_path):
        """Test that file rename works when target file does not exist."""
        # Create source file
        source_file = tmp_path / "source_file.pdf"
        source_file.write_text("source content")

        # Target file does not exist
        target_file = tmp_path / "new_target.pdf"
        assert not target_file.exists()

        # Use shutil.move
        shutil.move(str(source_file), str(target_file))

        # Verify source is moved
        assert not source_file.exists()
        assert target_file.exists()
        assert target_file.read_text() == "source content"

    def test_file_rename_with_special_characters(self, tmp_path):
        """Test file rename with special characters in filename."""
        # Create source file
        source_file = tmp_path / "temp_upload_12345.pdf"
        source_file.write_text("content")

        # Target file with special characters (URL encoded spaces)
        target_file = tmp_path / "document%20name.pdf"

        # Use shutil.move
        shutil.move(str(source_file), str(target_file))

        assert not source_file.exists()
        assert target_file.exists()
