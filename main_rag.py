"""
TechMart Product Q&A Assistant - RAG Version
Uses embeddings for semantic retrieval instead of hardcoded scoring.
"""

import os
import sys
from dotenv import load_dotenv
from llm_client import create_llm_client
from query_understanding import extract_query_info
from embedding_retrieval import EmbeddingRetriever
from answer_generation import generate_with_guardrails


# Load environment variables
load_dotenv()


def process_query_rag(
    query: str, 
    catalog_path: str = "data/catalog_50.json",  # Changed to 50-product catalog
    verbose: bool = False,
    retriever: EmbeddingRetriever = None
) -> dict:
    """
    Process a user query using RAG approach (embeddings for retrieval).
    
    Args:
        query: User's natural language question
        catalog_path: Path to catalog JSON file
        verbose: If True, print intermediate steps
        retriever: Pre-initialized retriever (for reuse)
    
    Returns:
        Dictionary with query_info, retrieved_products, and answer
    """
    # Initialize LLM client
    try:
        llm_client = create_llm_client()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set LLM_API_KEY in your .env file")
        sys.exit(1)
    
    # Stage 1: Query Understanding (LLM)
    if verbose:
        print("\n=== Stage 1: Query Understanding (LLM) ===")
    
    query_info = extract_query_info(query, llm_client)
    
    if verbose:
        print(f"Extracted info: {query_info}")
    
    # Stage 2: Retrieval using Embeddings (RAG approach)
    if verbose:
        print("\n=== Stage 2: Semantic Retrieval (Embeddings) ===")
    
    # Initialize retriever if not provided
    if retriever is None:
        retriever = EmbeddingRetriever()
        retriever.load_and_embed_catalog(catalog_path)
    
    retrieval_result = retriever.retrieve(query, query_info, max_results=8)
    products = retrieval_result["products"]
    no_results_reason = retrieval_result.get("no_results_reason")
    
    if verbose:
        print(f"Retrieved {len(products)} products")
        if products:
            print(f"Product IDs: {[p['id'] for p in products]}")
        if no_results_reason:
            print(f"Note: {no_results_reason}")
    
    # Stage 3: Answer Generation with Guardrails (LLM)
    if verbose:
        print("\n=== Stage 3: Answer Generation (LLM) ===")
    
    answer = generate_with_guardrails(
        query,
        products,
        llm_client,
        no_results_reason=no_results_reason
    )
    
    if verbose:
        print(f"Answer generated ({len(answer)} chars)")
    
    return {
        "query": query,
        "query_info": query_info,
        "products": products,
        "no_results_reason": no_results_reason,
        "answer": answer,
        "retriever": retriever  # Return for reuse
    }


def interactive_mode_rag(catalog_path: str = "data/catalog_50.json"):  # Changed to 50-product catalog
    """Run in interactive mode with RAG retrieval - continuous conversation."""
    print("=" * 60)
    print("TechMart Product Q&A Assistant (RAG Mode)")
    print("=" * 60)
    print(f"Using catalog: {catalog_path}")
    print("Loading embeddings (this may take a moment)...\n")
    
    # Initialize retriever once for all queries
    retriever = EmbeddingRetriever()
    retriever.load_and_embed_catalog(catalog_path)
    
    print("\nType your question or 'quit' to exit\n")
    
    while True:
        try:
            query = input("You: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Thank you for using TechMart Assistant!")
                break
            
            result = process_query_rag(query, catalog_path, verbose=False, retriever=retriever)
            print(f"\nAssistant: {result['answer']}\n")
            
        except KeyboardInterrupt:
            print("\n\nThank you for using TechMart Assistant!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def cli_mode_rag(query: str, catalog_path: str = "data/catalog_50.json", verbose: bool = False):  # Changed to 50-product catalog
    """Process a single query from command line using RAG."""
    result = process_query_rag(query, catalog_path, verbose=verbose)
    print(result['answer'])
    return result


def main():
    """Main entry point for RAG version."""
    if len(sys.argv) == 1:
        # No arguments - interactive mode
        catalog = os.getenv("CATALOG_PATH", "data/catalog_50.json")  # Changed to 50-product catalog
        interactive_mode_rag(catalog)
    elif len(sys.argv) == 2:
        # Single argument - process query
        query = sys.argv[1]
        catalog = os.getenv("CATALOG_PATH", "data/catalog_50.json")  # Changed to 50-product catalog
        cli_mode_rag(query, catalog, verbose=False)
    elif len(sys.argv) == 3 and sys.argv[1] == "--catalog":
        # Custom catalog in interactive mode
        catalog = sys.argv[2]
        interactive_mode_rag(catalog)
    elif len(sys.argv) == 3:
        # Query with custom catalog
        query = sys.argv[1]
        catalog = sys.argv[2]
        cli_mode_rag(query, catalog, verbose=False)
    elif len(sys.argv) >= 3 and sys.argv[1] == "--verbose":
        # Verbose mode
        query = sys.argv[2]
        catalog = sys.argv[3] if len(sys.argv) > 3 else "data/catalog_50.json"  # Changed to 50-product catalog
        cli_mode_rag(query, catalog, verbose=True)
    else:
        print("Usage:")
        print("  python main_rag.py                          # Interactive mode (RAG)")
        print("  python main_rag.py \"your question\"          # Single query")
        print("  python main_rag.py \"question\" catalog.json  # Custom catalog")
        print("  python main_rag.py --catalog catalog.json   # Interactive with custom catalog")
        print("  python main_rag.py --verbose \"question\"     # Verbose output")
        sys.exit(1)


if __name__ == "__main__":
    main()
