"""
End-to-end test for cognee memory integration.
Uses isolated data directory so it won't conflict with the running server.

Run: cd backend && ./venv/bin/python3 tests/test_cognee_memory.py
"""
import os
import sys
import asyncio
import tempfile

os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_cognee_e2e():
    import cognee

    # Use isolated data dir so we don't clash with running server's KuzuDB lock
    test_dir = tempfile.mkdtemp(prefix="cognee_test_")
    cognee.config.system_root_directory(test_dir)
    cognee.config.data_root_directory(os.path.join(test_dir, "data"))

    # Configure LLM — OpenAI (cognee's best-tested path) + local fastembed embeddings
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("SKIP: OPENAI_API_KEY not set")
        return

    cognee.config.set_llm_provider("openai")
    cognee.config.set_llm_api_key(api_key)
    cognee.config.set_llm_model("gpt-4o-mini")
    cognee.config.set_embedding_provider("fastembed")
    cognee.config.set_embedding_model("BAAI/bge-small-en-v1.5")
    cognee.config.set_embedding_dimensions(384)

    dataset = "test_user_memory"

    # 1. Remember
    print("1. cognee.remember()...", flush=True)
    await cognee.remember(
        "User holds AAPL, TSLA, and MSFT. Risk tolerance is moderate. "
        "Prefers growth stocks in tech sector. Recently sold NFLX at a loss for tax harvesting.",
        dataset_name=dataset,
        self_improvement=False,
    )
    print("   OK", flush=True)

    # 2. Recall
    print("2. cognee.recall()...", flush=True)
    results = await cognee.recall(
        query_text="What stocks does the user hold and what is their risk tolerance?",
        datasets=[dataset],
        top_k=10,
    )
    print(f"   Got {len(results)} results", flush=True)
    assert len(results) > 0, "Expected at least 1 recall result"
    for r in results[:3]:
        text = str(r)[:200]
        print(f"   - {text}", flush=True)

    # 3. Remember more (simulating a second chat)
    print("3. cognee.remember() second chat...", flush=True)
    await cognee.remember(
        "User asked about FIX (Comfort Systems). Interested in data center buildout theme. "
        "Considering adding industrial stocks to portfolio.",
        dataset_name=dataset,
        self_improvement=False,
    )
    print("   OK", flush=True)

    # 4. Recall should now include both chats
    print("4. cognee.recall() with accumulated knowledge...", flush=True)
    results2 = await cognee.recall(
        query_text="Synthesize everything known about this user: stocks, preferences, risk tolerance, sectors of interest.",
        datasets=[dataset],
        top_k=15,
    )
    print(f"   Got {len(results2)} results", flush=True)
    assert len(results2) > 0, "Expected recall results after second remember"
    for r in results2[:5]:
        text = str(r)[:200]
        print(f"   - {text}", flush=True)

    # 5. Cleanup
    print("5. Cleanup...", flush=True)
    try:
        await cognee.prune.prune_data(dataset)
    except Exception as e:
        print(f"   Cleanup warning (non-fatal): {e}", flush=True)

    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    print("   OK", flush=True)

    print("\nALL TESTS PASSED", flush=True)


if __name__ == "__main__":
    asyncio.run(test_cognee_e2e())
