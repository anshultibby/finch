#!/usr/bin/env python3
"""
Test script to verify Gemini API connectivity and model availability.

Usage:
    # From backend directory with venv activated:
    python scripts/test_gemini.py
    
    # Or with specific model:
    python scripts/test_gemini.py --model gemini/gemini-2.5-pro
"""
import asyncio
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from litellm import acompletion
from config import Config


# Available Gemini models to test (most useful ones)
GEMINI_MODELS = [
    "gemini/gemini-2.5-pro",           # Latest Gemini 2.5 Pro
    "gemini/gemini-2.5-flash",         # Fast Gemini 2.5
    "gemini/gemini-3-pro-preview",     # Gemini 3 Pro preview (if available)
    "gemini/gemini-2.0-flash",         # Gemini 2.0 Flash
    "gemini/gemini-1.5-pro",           # Gemini 1.5 Pro
]


async def test_gemini_model(model: str, api_key: str) -> dict:
    """Test a specific Gemini model."""
    print(f"\n{'='*60}")
    print(f"Testing: {model}")
    print(f"{'='*60}")
    
    try:
        response = await acompletion(
            model=model,
            api_key=api_key,
            messages=[
                {"role": "user", "content": "Say 'Hello from Gemini!' and tell me which model you are."}
            ],
            max_tokens=100,
        )
        
        content = response.choices[0].message.content or ""
        usage = response.usage
        
        print(f"✅ SUCCESS!")
        print(f"   Response: {content[:200]}{'...' if len(content) > 200 else ''}")
        if usage:
            input_tokens = getattr(usage, 'prompt_tokens', 0) or 0
            output_tokens = getattr(usage, 'completion_tokens', 0) or 0
            print(f"   Tokens: {input_tokens} input, {output_tokens} output")
        
        return {
            "model": model,
            "status": "success",
            "response": content,
            "tokens": {
                "input": getattr(usage, 'prompt_tokens', 0) if usage else 0,
                "output": getattr(usage, 'completion_tokens', 0) if usage else 0
            }
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"❌ FAILED: {error_msg[:200]}")
        traceback.print_exc()
        return {
            "model": model,
            "status": "failed",
            "error": error_msg
        }


async def test_streaming(model: str, api_key: str) -> bool:
    """Test streaming with a Gemini model."""
    print(f"\n{'='*60}")
    print(f"Testing STREAMING with: {model}")
    print(f"{'='*60}")
    
    try:
        stream = await acompletion(
            model=model,
            api_key=api_key,
            messages=[
                {"role": "user", "content": "Count from 1 to 5, one number per line."}
            ],
            max_tokens=50,
            stream=True,
        )
        
        print("   Streaming response: ", end="", flush=True)
        full_response = ""
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        
        print()  # newline
        print(f"✅ Streaming works!")
        return True
        
    except Exception as e:
        print(f"❌ Streaming failed: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test Gemini API connectivity")
    parser.add_argument(
        "--model", 
        type=str, 
        default=None,
        help="Specific model to test (e.g., gemini/gemini-2.5-pro)"
    )
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Test all available Gemini models"
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Also test streaming mode"
    )
    args = parser.parse_args()
    
    # Check for API key
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not set!")
        print()
        print("To fix this, add to your .env file:")
        print("  GEMINI_API_KEY=your_api_key_here")
        print()
        print("Get your API key from: https://aistudio.google.com/apikey")
        sys.exit(1)
    
    print("🔑 GEMINI_API_KEY is set")
    print(f"   Key prefix: {api_key[:8]}...")
    
    # Determine which models to test
    if args.model:
        models_to_test = [args.model]
    elif args.all:
        models_to_test = GEMINI_MODELS
    else:
        # Default: test the main recommended model
        models_to_test = ["gemini/gemini-2.5-pro"]
    
    print(f"\n📋 Testing {len(models_to_test)} model(s)...")
    
    # Run tests
    results = []
    for model in models_to_test:
        result = await test_gemini_model(model, api_key)
        results.append(result)
    
    # Test streaming if requested
    if args.streaming and results and results[0]["status"] == "success":
        await test_streaming(models_to_test[0], api_key)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"✅ Passed: {success_count}/{len(results)}")
    
    if success_count < len(results):
        print(f"❌ Failed: {len(results) - success_count}/{len(results)}")
        for r in results:
            if r["status"] == "failed":
                print(f"   - {r['model']}: {r['error'][:100]}")
    
    # Show recommended usage
    if success_count > 0:
        working_model = next(r["model"] for r in results if r["status"] == "success")
        print(f"\n💡 To use Gemini in your app, set in .env:")
        print(f"   PLANNER_LLM_MODEL={working_model}")
        print(f"   # or")
        print(f"   EXECUTOR_LLM_MODEL={working_model}")
    
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

