"""
Embedding-based Retrieval (RAG approach)
Uses sentence embeddings for semantic similarity instead of hardcoded scoring.
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingRetriever:
    """RAG-style retriever using embeddings for semantic search."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model.
        
        Args:
            model_name: HuggingFace model name (default is fast & good quality)
        """
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.product_embeddings = None
        self.products = None
    
    def load_and_embed_catalog(self, catalog_path: str):
        """
        Load catalog and create embeddings for all products.
        
        Args:
            catalog_path: Path to catalog JSON file
        
        Raises:
            FileNotFoundError: If catalog doesn't exist
            ValueError: If catalog is invalid
        """
        print(f"Loading catalog from {catalog_path}...")
        
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                self.products = json.load(f)
            
            if not self.products or not isinstance(self.products, list):
                raise ValueError("Catalog must be a non-empty list")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Catalog file not found: {catalog_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in catalog: {e}")
        
        # Create rich text description for each product
        product_texts = []
        for product in self.products:
            # Combine name, category, specs, and description for embedding
            text = f"{product.get('name', '')} {product.get('category', '')} "
            text += f"Price: ₹{product.get('price_inr', 0)} "
            
            # Add specs
            specs = product.get('specs', {})
            for key, value in specs.items():
                if value:
                    text += f"{key.replace('_', ' ')}: {value} "
            
            # Add description
            text += product.get('description', '')
            
            product_texts.append(text)
        
        print(f"Creating embeddings for {len(product_texts)} products...")
        try:
            self.product_embeddings = self.model.encode(product_texts, show_progress_bar=True)
            print("✅ Embeddings ready!")
        except Exception as e:
            raise RuntimeError(f"Failed to create embeddings: {e}")
    
    def retrieve(
        self,
        query: str,
        query_info: Dict[str, Any],
        max_results: int = 8
    ) -> Dict[str, Any]:
        """
        Retrieve products using embeddings + hard filters.
        
        Args:
            query: Original user query
            query_info: Extracted filters (category, price, etc.)
            max_results: Max products to return
        
        Returns:
            Dict with products and optional no_results_reason
        """
        if self.products is None or self.product_embeddings is None:
            raise ValueError("Catalog not loaded. Call load_and_embed_catalog first.")
        
        # Step 1: Apply HARD FILTERS (price, category) - Python
        filtered_products = []
        filtered_embeddings = []
        
        for i, product in enumerate(self.products):
            # Category filter
            if query_info.get('category'):
                if product['category'] != query_info['category']:
                    continue
            
            # Price filters
            price = product['price_inr']
            if query_info.get('price_min') and price < query_info['price_min']:
                continue
            if query_info.get('price_max') and price > query_info['price_max']:
                continue
            
            filtered_products.append(product)
            filtered_embeddings.append(self.product_embeddings[i])
        
        # Check if filters yielded no results
        if not filtered_products:
            if query_info.get('price_max'):
                # Find near-miss products
                near_miss = []
                for product in self.products:
                    if product['category'] == query_info.get('category'):
                        if product['price_inr'] > query_info['price_max']:
                            near_miss.append(product)
                
                near_miss.sort(key=lambda p: p['price_inr'])
                return {
                    "products": near_miss[:3],
                    "no_results_reason": f"No products found under ₹{query_info['price_max']}. Here are the closest options above your budget:"
                }
            
            return {
                "products": [],
                "no_results_reason": "No products match your criteria."
            }
        
        # Step 2: SEMANTIC RANKING using embeddings - AI decides
        print(f"Filtered to {len(filtered_products)} products, ranking by semantic similarity...")
        
        # Encode query
        query_embedding = self.model.encode([query])
        
        # Calculate cosine similarity between query and filtered products
        filtered_embeddings = np.array(filtered_embeddings)
        similarities = cosine_similarity(query_embedding, filtered_embeddings)[0]
        
        # Rank by similarity
        ranked_indices = np.argsort(similarities)[::-1]  # Descending order
        
        # Get top products
        top_products = [filtered_products[i] for i in ranked_indices[:max_results]]
        
        # Debug info
        print(f"Top products by semantic similarity:")
        for i, idx in enumerate(ranked_indices[:5], 1):
            print(f"  {i}. {filtered_products[idx]['name']} (similarity: {similarities[idx]:.3f})")
        
        return {"products": top_products}


def retrieve_with_embeddings(
    catalog_path: str,
    query: str,
    query_info: Dict[str, Any],
    max_results: int = 8,
    retriever: Optional[EmbeddingRetriever] = None
) -> Dict[str, Any]:
    """
    Main function for embedding-based retrieval.
    
    Args:
        catalog_path: Path to catalog JSON
        query: User's natural language query
        query_info: Extracted query information
        max_results: Max products to return
        retriever: Optional pre-initialized retriever (for reuse)
    
    Returns:
        Dict with products and optional no_results_reason
    """
    if retriever is None:
        retriever = EmbeddingRetriever()
        retriever.load_and_embed_catalog(catalog_path)
    
    return retriever.retrieve(query, query_info, max_results)
