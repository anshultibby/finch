"""Test JSON parsing with markdown code fences"""
import pytest
import json
from services.strategy_executor import strip_markdown_code_fences


class TestMarkdownCodeFenceStripping:
    """Test the strip_markdown_code_fences function"""
    
    def test_strip_json_code_fence(self):
        """Test stripping ```json...``` markdown fences"""
        input_text = """```json
{
    "action": "CONTINUE",
    "signal": "BEARISH",
    "signal_value": 0.3,
    "reasoning": "Test reasoning",
    "confidence": 60
}
```"""
        
        expected = """{
    "action": "CONTINUE",
    "signal": "BEARISH",
    "signal_value": 0.3,
    "reasoning": "Test reasoning",
    "confidence": 60
}"""
        
        result = strip_markdown_code_fences(input_text)
        assert result == expected
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed["action"] == "CONTINUE"
        assert parsed["signal"] == "BEARISH"
        assert parsed["signal_value"] == 0.3
    
    def test_strip_generic_code_fence(self):
        """Test stripping generic ``` fences without language tag"""
        input_text = """```
{
    "action": "BUY",
    "confidence": 80
}
```"""
        
        expected = """{
    "action": "BUY",
    "confidence": 80
}"""
        
        result = strip_markdown_code_fences(input_text)
        assert result == expected
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed["action"] == "BUY"
    
    def test_no_code_fence(self):
        """Test that plain JSON is left unchanged"""
        input_text = """{
    "action": "HOLD",
    "signal": "NEUTRAL"
}"""
        
        result = strip_markdown_code_fences(input_text)
        assert result == input_text
        
        # Verify it's valid JSON
        parsed = json.loads(result)
        assert parsed["action"] == "HOLD"
    
    def test_whitespace_handling(self):
        """Test that extra whitespace is properly handled"""
        input_text = """  ```json
{
    "action": "SKIP"
}
```  """
        
        result = strip_markdown_code_fences(input_text)
        
        # Should be valid JSON after stripping
        parsed = json.loads(result)
        assert parsed["action"] == "SKIP"
    
    def test_real_world_example(self):
        """Test with the exact format from the bug report"""
        input_text = """```json
{
    "action": "CONTINUE",
    "signal": "BEARISH",
    "signal_value": 0.3,
    "reasoning": "Last 2 quarters revenue growth: Q2 2025: +4.30%, Q1 2025: -40.14%. Average revenue growth = -17.92%, which is negative. However, there's strong momentum improvement from Q1 to Q2 (from -40% to +4%), suggesting a turnaround. Despite the negative average, the recent Q2 positive growth shows recovery momentum relevant to a 'Black Friday Consumer Rebound' strategy. Since the average is negative per strict rule logic, this is BEARISH, but the strong sequential improvement warrants continuing evaluation rather than immediate skip.",
    "confidence": 60
}
```"""
        
        result = strip_markdown_code_fences(input_text)
        
        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["action"] == "CONTINUE"
        assert parsed["signal"] == "BEARISH"
        assert parsed["signal_value"] == 0.3
        assert parsed["confidence"] == 60
        assert "Q2 2025: +4.30%" in parsed["reasoning"]
    
    def test_only_opening_fence(self):
        """Test handling of malformed markdown with only opening fence"""
        input_text = """```json
{
    "action": "SELL"
}"""
        
        result = strip_markdown_code_fences(input_text)
        
        # Should still be valid JSON
        parsed = json.loads(result)
        assert parsed["action"] == "SELL"
    
    def test_nested_code_blocks_in_string(self):
        """Test JSON containing code blocks in string values"""
        input_text = """```json
{
    "action": "BUY",
    "reasoning": "Example: ```code``` within reasoning"
}
```"""
        
        result = strip_markdown_code_fences(input_text)
        
        # Should preserve the ``` in the string value
        parsed = json.loads(result)
        assert "```code```" in parsed["reasoning"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

