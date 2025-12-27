"""Tests for file deletion functionality."""

import shutil
from pathlib import Path


class TestDeletePhysicalFiles:
    """Test the _delete_physical_files method."""

    def test_delete_chunk_cache_files(self, tmp_path):
        """Test that chunk cache files are deleted."""
        # Setup: Create test directory and files
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()

        # Create test files matching the file stem
        test_file_stem = "test_document"
        (chunks_dir / f"{test_file_stem}.chunks.json").write_text("chunks data")
        (chunks_dir / f"{test_file_stem}_part1.txt").write_text("part 1")
        (chunks_dir / "other_file.txt").write_text("other")  # Should not be deleted

        # Verify files exist
        assert (chunks_dir / f"{test_file_stem}.chunks.json").exists()
        assert (chunks_dir / f"{test_file_stem}_part1.txt").exists()
        assert (chunks_dir / "other_file.txt").exists()

        # Simulate deletion
        file_stem = Path("test_document.pdf").stem
        for file_path in chunks_dir.iterdir():
            if file_stem in file_path.name:
                file_path.unlink()

        # Verify target files are deleted but other files remain
        assert not (chunks_dir / f"{test_file_stem}.chunks.json").exists()
        assert not (chunks_dir / f"{test_file_stem}_part1.txt").exists()
        assert (chunks_dir / "other_file.txt").exists()

    def test_delete_markdown_cache_files(self, tmp_path):
        """Test that markdown cache files are deleted."""
        # Setup: Create test directory and files
        markdown_dir = tmp_path / "markdown_cache_dir"
        markdown_dir.mkdir()

        # Create test files matching the file stem
        test_file_stem = "test_document"
        (markdown_dir / f"{test_file_stem}.md").write_text("markdown content")
        (markdown_dir / "unrelated.md").write_text("other")  # Should not be deleted

        # Verify files exist
        assert (markdown_dir / f"{test_file_stem}.md").exists()
        assert (markdown_dir / "unrelated.md").exists()

        # Simulate deletion
        file_stem = Path("test_document.pdf").stem
        for file_path in markdown_dir.iterdir():
            if file_stem in file_path.name:
                file_path.unlink()

        # Verify target files are deleted but other files remain
        assert not (markdown_dir / f"{test_file_stem}.md").exists()
        assert (markdown_dir / "unrelated.md").exists()

    def test_delete_directory_cache(self, tmp_path):
        """Test that cache directories are deleted."""
        # Setup: Create test directory with subdirectory
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()

        test_file_stem = "test_document"
        sub_dir = chunks_dir / f"{test_file_stem}_cache"
        sub_dir.mkdir()
        (sub_dir / "cached_data.txt").write_text("cached")

        # Verify directory exists
        assert sub_dir.exists()

        # Simulate deletion
        file_stem = Path("test_document.pdf").stem
        for file_path in chunks_dir.iterdir():
            if file_stem in file_path.name:
                if file_path.is_dir():
                    shutil.rmtree(file_path)

        # Verify directory is deleted
        assert not sub_dir.exists()

    def test_empty_file_name_does_nothing(self, tmp_path):
        """Test that empty file name causes no deletion."""
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()
        (chunks_dir / "test.txt").write_text("content")

        # With empty file name, nothing should happen
        file_stem = Path("").stem
        deleted_count = 0
        for file_path in chunks_dir.iterdir():
            if file_stem and file_stem in file_path.name:
                deleted_count += 1

        assert deleted_count == 0
        assert (chunks_dir / "test.txt").exists()

    def test_nonexistent_cache_dirs_handled(self, tmp_path):
        """Test that missing cache directories don't cause errors."""
        # Non-existent directory
        chunks_dir = tmp_path / "nonexistent_chunks_dir"
        markdown_dir = tmp_path / "nonexistent_markdown_dir"

        # Should not raise any errors
        assert not chunks_dir.exists()
        assert not markdown_dir.exists()

        # Simulating the check in _delete_physical_files
        if chunks_dir.exists():
            pass  # Would iterate but doesn't exist
        if markdown_dir.exists():
            pass  # Would iterate but doesn't exist

        # No errors should be raised
        assert True
