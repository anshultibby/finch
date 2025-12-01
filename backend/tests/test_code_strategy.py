"""
Test Code-Based Strategies

This tests the new code generation approach which is:
- Much faster (no LLM calls during execution)
- Deterministic (same inputs → same outputs)
- Debuggable (can inspect actual code)
- Perfect for backtesting
"""
import pytest
import asyncio
from modules.strategy_code_generator import strategy_code_generator
from modules.code_sandbox import code_sandbox
from modules.resource_manager import resource_manager


@pytest.mark.asyncio
async def test_generate_screening_code():
    """Test generating screening code from natural language"""
    
    result = await strategy_code_generator.generate_screening_code(
        strategy_description="Buy technology stocks with revenue growth > 20%",
        data_sources=["income-statement", "key-metrics"]
    )
    
    print("\n=== Generated Screening Code ===")
    print(result["code"])
    print("\n=== Explanation ===")
    print(result["explanation"])
    
    assert result["success"], f"Code generation failed: {result.get('error')}"
    assert "def screen" in result["code"]
    assert "return" in result["code"]


@pytest.mark.asyncio
async def test_generate_management_code():
    """Test generating management code"""
    
    result = await strategy_code_generator.generate_management_code(
        strategy_description="Exit when profit >= 25% or loss >= -10%",
        risk_params={
            "stop_loss_pct": 10,
            "take_profit_pct": 25,
            "max_hold_days": 90
        }
    )
    
    print("\n=== Generated Management Code ===")
    print(result["code"])
    
    assert result["success"], f"Code generation failed: {result.get('error')}"
    assert "def manage" in result["code"]


def test_sandbox_validation():
    """Test code sandbox validation"""
    
    # Valid code
    valid_code = """
def screen(ticker: str, data: dict) -> dict:
    return {"action": "BUY", "signal": "BULLISH", "confidence": 80, "reason": "Test"}
"""
    
    is_valid, error = code_sandbox.validate_code(valid_code)
    assert is_valid, f"Valid code rejected: {error}"
    
    # Invalid code - dangerous import
    dangerous_code = """
import os
def screen(ticker: str, data: dict) -> dict:
    os.system("rm -rf /")
    return {"action": "BUY"}
"""
    
    is_valid, error = code_sandbox.validate_code(dangerous_code)
    assert not is_valid
    assert "os" in error.lower()
    
    # Invalid code - file I/O
    file_io_code = """
def screen(ticker: str, data: dict) -> dict:
    with open("/etc/passwd", "r") as f:
        data = f.read()
    return {"action": "BUY"}
"""
    
    is_valid, error = code_sandbox.validate_code(file_io_code)
    assert not is_valid
    assert "file" in error.lower() or "open" in error.lower()


def test_sandbox_execution():
    """Test executing code in sandbox"""
    
    code = """
def screen(ticker: str, data: dict) -> dict:
    # Simple logic: buy if price < 100
    price = data.get("price", 0)
    
    if price < 100:
        return {
            "action": "BUY",
            "signal": "BULLISH",
            "confidence": 80,
            "reason": f"Good price: ${price}"
        }
    else:
        return {
            "action": "SKIP",
            "signal": "NEUTRAL",
            "confidence": 60,
            "reason": f"Price too high: ${price}"
        }
"""
    
    # Test BUY case
    result = code_sandbox.execute_function(
        code,
        "screen",
        ticker="AAPL",
        data={"price": 50}
    )
    
    assert result["success"]
    assert result["result"]["action"] == "BUY"
    assert result["result"]["confidence"] == 80
    
    # Test SKIP case
    result = code_sandbox.execute_function(
        code,
        "screen",
        ticker="AAPL",
        data={"price": 150}
    )
    
    assert result["success"]
    assert result["result"]["action"] == "SKIP"


def test_resource_manager():
    """Test file system operations"""
    
    test_user = "test_user_123"
    test_chat = "test_chat_456"
    
    # Write chat file
    path = resource_manager.write_chat_file(
        test_user,
        test_chat,
        "test.txt",
        "Hello, world!"
    )
    assert path is not None
    
    # Read chat file
    content = resource_manager.read_chat_file(
        test_user,
        test_chat,
        "test.txt"
    )
    assert content == "Hello, world!"
    
    # List chat files
    files = resource_manager.list_chat_files(test_user, test_chat)
    assert len(files) >= 1
    assert any(f["name"] == "test.txt" for f in files)
    
    # Delete chat file
    deleted = resource_manager.delete_chat_file(test_user, test_chat, "test.txt")
    assert deleted
    
    # Verify deletion
    content = resource_manager.read_chat_file(test_user, test_chat, "test.txt")
    assert content is None


def test_save_strategy_as_markdown():
    """Test saving strategy as markdown file"""
    
    test_user = "test_user_123"
    
    screening_code = """
def screen(ticker: str, data: dict) -> dict:
    return {"action": "BUY", "signal": "BULLISH", "confidence": 80, "reason": "Test"}
"""
    
    management_code = """
def manage(ticker: str, position: dict, data: dict) -> dict:
    if position["pnl_pct"] >= 25:
        return {"action": "SELL", "signal": "NEUTRAL", "confidence": 100, "reason": "Take profit"}
    return {"action": "HOLD", "signal": "NEUTRAL", "confidence": 70, "reason": "Hold"}
"""
    
    # Save strategy
    path = resource_manager.save_strategy(
        test_user,
        "Test Strategy",
        "This is a test strategy",
        screening_code,
        management_code,
        metadata={"budget": 1000, "max_positions": 5}
    )
    
    assert path is not None
    print(f"\nSaved strategy to: {path}")
    
    # Get strategy
    content = resource_manager.get_strategy(test_user, "Test Strategy")
    assert content is not None
    assert "# Strategy: Test Strategy" in content
    assert "def screen" in content
    assert "def manage" in content
    
    # List strategies
    strategies = resource_manager.list_strategies(test_user)
    assert len(strategies) >= 1
    assert any(s["name"] == "Test Strategy" for s in strategies)
    
    # Delete strategy
    deleted = resource_manager.delete_strategy(test_user, "Test Strategy")
    assert deleted


if __name__ == "__main__":
    # Run tests
    print("\n" + "="*60)
    print("Testing Code-Based Strategy System")
    print("="*60)
    
    print("\n1. Testing code sandbox...")
    test_sandbox_validation()
    test_sandbox_execution()
    print("   ✓ Sandbox tests passed")
    
    print("\n2. Testing resource manager...")
    test_resource_manager()
    test_save_strategy_as_markdown()
    print("   ✓ Resource manager tests passed")
    
    print("\n3. Testing code generation...")
    asyncio.run(test_generate_screening_code())
    asyncio.run(test_generate_management_code())
    print("   ✓ Code generation tests passed")
    
    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)

