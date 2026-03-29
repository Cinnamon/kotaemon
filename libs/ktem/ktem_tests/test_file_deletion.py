"""Tests for file deletion functionality."""

import shutil
from pathlib import Path
from unittest.mock import patch

from ktem.index.file.ui import FileIndexPage


class TestDeletePhysicalFiles:
    """Test the _delete_physical_files method."""

    def test_delete_chunk_cache_files(self, tmp_path):
        """Test that chunk cache files are deleted."""
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()
        markdown_dir = tmp_path / "markdown_cache_dir"
        markdown_dir.mkdir()

        test_file_stem = "test_document"
        (chunks_dir / f"{test_file_stem}.chunks.json").write_text("chunks data")
        (chunks_dir / f"{test_file_stem}_part1.txt").write_text("part 1")
        (chunks_dir / "other_file.txt").write_text("other")

        assert (chunks_dir / f"{test_file_stem}.chunks.json").exists()
        assert (chunks_dir / f"{test_file_stem}_part1.txt").exists()
        assert (chunks_dir / "other_file.txt").exists()

        page = FileIndexPage.__new__(FileIndexPage)
        
        with patch("ktem.index.file.ui.flowsettings") as mock_settings:
            mock_settings.KH_CHUNKS_OUTPUT_DIR = str(chunks_dir)
            mock_settings.KH_MARKDOWN_OUTPUT_DIR = str(markdown_dir)
            page._delete_physical_files("test_document.pdf")

        assert not (chunks_dir / f"{test_file_stem}.chunks.json").exists()
        assert not (chunks_dir / f"{test_file_stem}_part1.txt").exists()
        assert (chunks_dir / "other_file.txt").exists()

    def test_delete_markdown_cache_files(self, tmp_path):
        """Test that markdown cache files are deleted."""
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()
        markdown_dir = tmp_path / "markdown_cache_dir"
        markdown_dir.mkdir()

        test_file_stem = "test_document"
        (markdown_dir / f"{test_file_stem}.md").write_text("markdown content")
        (markdown_dir / "unrelated.md").write_text("other")

        assert (markdown_dir / f"{test_file_stem}.md").exists()
        assert (markdown_dir / "unrelated.md").exists()

        page = FileIndexPage.__new__(FileIndexPage)

        with patch("ktem.index.file.ui.flowsettings") as mock_settings:
            mock_settings.KH_CHUNKS_OUTPUT_DIR = str(chunks_dir)
            mock_settings.KH_MARKDOWN_OUTPUT_DIR = str(markdown_dir)
            page._delete_physical_files("test_document.pdf")

        assert not (markdown_dir / f"{test_file_stem}.md").exists()
        assert (markdown_dir / "unrelated.md").exists()

    def test_delete_directory_cache(self, tmp_path):
        """Test that cache directories are deleted."""
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()
        markdown_dir = tmp_path / "markdown_cache_dir"
        markdown_dir.mkdir()

        test_file_stem = "test_document"
        sub_dir = chunks_dir / f"{test_file_stem}_cache"
        sub_dir.mkdir()
        (sub_dir / "cached_data.txt").write_text("cached")

        assert sub_dir.exists()

        page = FileIndexPage.__new__(FileIndexPage)

        with patch("ktem.index.file.ui.flowsettings") as mock_settings:
            mock_settings.KH_CHUNKS_OUTPUT_DIR = str(chunks_dir)
            mock_settings.KH_MARKDOWN_OUTPUT_DIR = str(markdown_dir)
            page._delete_physical_files("test_document.pdf")

        assert not sub_dir.exists()

    def test_empty_file_name_does_nothing(self, tmp_path):
        """Test that empty file name causes no deletion."""
        chunks_dir = tmp_path / "chunks_cache_dir"
        chunks_dir.mkdir()
        markdown_dir = tmp_path / "markdown_cache_dir"
        markdown_dir.mkdir()
        (chunks_dir / "test.txt").write_text("content")

        page = FileIndexPage.__new__(FileIndexPage)

        with patch("ktem.index.file.ui.flowsettings") as mock_settings:
            mock_settings.KH_CHUNKS_OUTPUT_DIR = str(chunks_dir)
            mock_settings.KH_MARKDOWN_OUTPUT_DIR = str(markdown_dir)
            page._delete_physical_files("")

        assert (chunks_dir / "test.txt").exists()

    def test_nonexistent_cache_dirs_handled(self, tmp_path):
        """Test that missing cache directories don't cause errors."""
        chunks_dir = tmp_path / "nonexistent_chunks_dir"
        markdown_dir = tmp_path / "nonexistent_markdown_dir"

        page = FileIndexPage.__new__(FileIndexPage)

        with patch("ktem.index.file.ui.flowsettings") as mock_settings:
            mock_settings.KH_CHUNKS_OUTPUT_DIR = str(chunks_dir)
            mock_settings.KH_MARKDOWN_OUTPUT_DIR = str(markdown_dir)
            # Should not raise any errors
            page._delete_physical_files("test_document.pdf")

        # No operation should create any new files or directories
        # If an error were raised, the test would fail; here we assert that
        # the temporary directory remains empty.
        assert list(tmp_path.iterdir()) == []
