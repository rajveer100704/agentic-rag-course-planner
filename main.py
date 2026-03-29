"""
main.py — Entry point for the RAG Prerequisite & Course Planning Assistant.

Usage:
    # Build index (first time):
    python main.py --build

    # Interactive mode:
    python main.py --interactive

    # Single query:
    python main.py --query "Can I take CS 310 if I've completed CS 201 and CS 250?"

    # Run evaluation:
    python main.py --evaluate
"""

import sys
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion import ingest_catalog, save_chunks
from vector_store import build_store, load_store, VectorStore
from agents import StudentProfile, run_pipeline
from formatter import format_response


INDEX_PATH = Path(__file__).parent / "outputs" / "vector_index.json"
CHUNKS_PATH = Path(__file__).parent / "outputs" / "chunks.json"


def build_index() -> VectorStore:
    print("=" * 60)
    print("Building RAG index...")
    print("=" * 60)
    chunks = ingest_catalog()
    save_chunks(chunks, CHUNKS_PATH)
    store = build_store(chunks, INDEX_PATH)
    print(f"\n✅ Index built successfully!")
    print(f"   Chunks: {len(chunks)}")
    print(f"   Index: {INDEX_PATH}")
    return store


def get_store() -> VectorStore:
    if INDEX_PATH.exists():
        print(f"[Main] Loading existing index from {INDEX_PATH}")
        return load_store(INDEX_PATH)
    else:
        return build_index()


def run_query(query: str, profile: StudentProfile, store: VectorStore,
              verbose: bool = False) -> str:
    result = run_pipeline(query, profile, store, verbose=verbose)
    return format_response(result), result


def interactive_mode(store: VectorStore):
    print("\n" + "=" * 70)
    print("🎓 Prerequisite & Course Planning Assistant")
    print("   State University Academic Catalog RAG System")
    print("=" * 70)
    print("Type your question or 'quit' to exit.")
    print("Type 'profile' to set your student profile.")
    print("Type 'reset' to reset your profile.\n")

    profile = StudentProfile()

    while True:
        try:
            user_input = input("\n📚 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("Goodbye!")
            break
        if user_input.lower() == "reset":
            profile = StudentProfile()
            print("Profile reset.")
            continue
        if user_input.lower() == "profile":
            print(f"Current profile: {json.dumps(profile.to_dict(), indent=2)}")
            continue

        formatted, raw = run_query(user_input, profile, store, verbose=False)
        print("\n" + "-" * 70)
        print(formatted)
        print("-" * 70)

        # Update profile from this interaction
        profile = raw.get("profile", profile)


def run_evaluation(store: VectorStore) -> None:
    """Run the 25-query evaluation set."""
    from evaluation.test_queries import get_test_queries, evaluate_response
    from evaluation.eval_runner import run_full_evaluation
    run_full_evaluation(store)


def main():
    parser = argparse.ArgumentParser(
        description="RAG Prerequisite & Course Planning Assistant"
    )
    parser.add_argument("--build", action="store_true",
                        help="Build/rebuild the vector index")
    parser.add_argument("--interactive", action="store_true",
                        help="Run interactive assistant")
    parser.add_argument("--query", type=str,
                        help="Run a single query")
    parser.add_argument("--evaluate", action="store_true",
                        help="Run the evaluation set")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose agent output")
    args = parser.parse_args()

    if args.build:
        build_index()
        return

    store = get_store()

    if args.query:
        profile = StudentProfile()
        profile.major = "B.S. Computer Science"
        formatted, _ = run_query(args.query, profile, store, verbose=args.verbose)
        print(formatted)

    elif args.evaluate:
        run_evaluation(store)

    else:
        # Default: interactive
        interactive_mode(store)


if __name__ == "__main__":
    main()
