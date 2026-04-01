"""Tests for decompose_question functionality."""

from ktem.reasoning.prompt_optimization.decompose_question import (
    DecomposeQuestionPipeline,
    _is_tool_not_supported_error,
)


class TestIsToolNotSupportedError:
    """Test the _is_tool_not_supported_error helper function."""

    def test_detects_ollama_error(self):
        """Test detection of Ollama's 'does not support tools' error."""
        error = Exception(
            "Error code: 400 - {'error': {'message': "
            "'registry.ollama.ai/library/deepseek-r1:7b does not support tools'}}"
        )
        assert _is_tool_not_supported_error(error) is True

    def test_detects_tool_use_not_supported(self):
        """Test detection of 'tool use is not supported' error."""
        error = Exception("Tool use is not supported by this model")
        assert _is_tool_not_supported_error(error) is True

    def test_detects_tools_are_not_supported(self):
        """Test detection of 'tools are not supported' error."""
        error = Exception("Tools are not supported for this model type")
        assert _is_tool_not_supported_error(error) is True

    def test_case_insensitive(self):
        """Test that detection is case insensitive."""
        error = Exception("DOES NOT SUPPORT TOOLS")
        assert _is_tool_not_supported_error(error) is True

    def test_other_errors_not_detected(self):
        """Test that unrelated errors are not detected as tool support issues."""
        error = Exception("Connection timeout")
        assert _is_tool_not_supported_error(error) is False

        error = Exception("Invalid API key")
        assert _is_tool_not_supported_error(error) is False

        error = Exception("Rate limit exceeded")
        assert _is_tool_not_supported_error(error) is False


class TestDecomposeQuestionPipelineFallback:
    """Test the fallback behavior for models without tool support."""

    def test_fallback_prompt_exists(self):
        """Test that fallback prompt template is defined."""
        assert hasattr(DecomposeQuestionPipeline, "DECOMPOSE_FALLBACK_PROMPT_TEMPLATE")
        assert (
            "JSON array" in DecomposeQuestionPipeline.DECOMPOSE_FALLBACK_PROMPT_TEMPLATE
        )

    def test_run_with_fallback_method_exists(self):
        """Test that _run_with_fallback method is defined."""
        assert hasattr(DecomposeQuestionPipeline, "_run_with_fallback")
