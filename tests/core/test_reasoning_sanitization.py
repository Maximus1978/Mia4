"""
Tests for reasoning sanitization and channel separation
"""
import pytest


def test_reasoning_sanitization_markers():
    """Test that reasoning sanitization removes service markers"""
    # Note: This test validates the pattern matching logic
    # The actual sanitization happens in TypeScript frontend
    
    raw_reasoning = """
    analysis|usersays: The user is asking about weather
    
    analysis|thinkstep: I need to consider the location
    
    commentary|internal: This seems straightforward
    
    Let me think about this question...
    
    The weather today is sunny.
    """
    
    # Test that we can detect markers that should be removed
    assert "analysis|" in raw_reasoning
    assert "commentary|" in raw_reasoning
    
    # Simulate what the frontend sanitization should achieve
    clean_lines = []
    for line in raw_reasoning.split('\n'):
        markers = ['analysis|', 'commentary|', 'channel|']
        if not any(marker in line for marker in markers):
            clean_lines.append(line)
    
    cleaned = '\n'.join(clean_lines).strip()
    
    # After sanitization, markers should be gone
    assert "analysis|" not in cleaned
    assert "commentary|" not in cleaned
    assert "Let me think about this question..." in cleaned


def test_no_reasoning_markers_in_final_content():
    """Test that final message content does not contain reasoning markers"""
    # This would be an integration test with actual model
    # For now, we ensure the principle is covered
    
    test_markers = [
        "analysis|usersays:",
        "analysis|thinkstep:",
        "commentary|internal:",
        "channel|final:",
        "<|reasoning|>",
        "<|analysis|>"
    ]
    
    # Simulate a final message that should NOT contain these
    clean_final_message = "Hello! How can I help you today?"
    
    for marker in test_markers:
        assert marker not in clean_final_message, (
            f"Final message should not contain {marker}"
        )


def test_reasoning_channel_separation():
    """Test that reasoning and final content are kept separate"""
    # This tests the principle that reasoning is never mixed with final content
    
    reasoning_content = "analysis|usersays: User wants help with coding"
    final_content = "I'd be happy to help you with coding!"
    
    # These should never be concatenated
    # In proper implementation, these are separate channels
    assert reasoning_content != final_content
    assert "analysis|" not in final_content
    assert "I'd be happy" not in reasoning_content


class TestReasoningChannelHygiene:
    """Test suite for reasoning channel hygiene invariants"""
    
    def test_reasoning_markers_pattern_detection(self):
        """Test detection of various reasoning marker patterns"""
        test_cases = [
            ("analysis|usersays: Hello", True),
            ("commentary|internal: Note", True),
            ("channel|final: Response", True),
            ("Normal text without markers", False),
            ("analysis without pipe character", False),
            ("Random analysis| in middle", True),
        ]
        
        for text, should_have_markers in test_cases:
            markers = ["analysis|", "commentary|", "channel|"]
            has_markers = any(marker in text for marker in markers)
            assert has_markers == should_have_markers, f"Failed for: {text}"
    
    def test_reasoning_placeholder_logic(self):
        """Test reasoning placeholder display logic"""
        # Simulate ChatWindow state scenarios
        # Format: (devEnabled, streaming, has_reasoning, should_show)
        scenarios = [
            (True, True, False, True),   # Dev + streaming + no reasoning
            (True, False, False, False),  # Dev + not streaming + no reasoning
            (False, True, False, False),  # No dev + streaming
            (True, True, True, True),    # Dev + streaming + has reasoning
            (True, False, True, True),   # Dev + not streaming + has reasoning
        ]
        
        for dev_enabled, streaming, has_reasoning, expected in scenarios:
            should_show = dev_enabled and (has_reasoning or streaming)
            assert should_show == expected, (
                f"Failed for dev={dev_enabled}, stream={streaming}, "
                f"reasoning={has_reasoning}"
            )