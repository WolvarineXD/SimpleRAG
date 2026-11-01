"""
Query Understanding - Extracts structured information from natural language queries.
Uses LLM to extract: category, price range, use case, product names, and attributes.
"""

import json
import re
from typing import Dict, Any, Optional, List
from llm_client import LLMClient


QUERY_UNDERSTANDING_PROMPT = """You are a query analyzer for an electronics e-commerce store in India.

Extract the following information from the user's query and return it as JSON:

{
  "category": "<laptop|earbuds|headset|smartphone|smartwatch|tablet|speaker|accessories or null>",
  "price_min": <number or null>,
  "price_max": <number or null>,
  "use_case": "<coding|video_editing|student|gaming|music|general or null>",
  "product_names": [<list of specific product names mentioned, or empty list>],
  "attributes": [<list of important attributes like 'battery', 'ANC', 'GPU', 'RAM', 'wireless', etc., or empty list>]
}

Rules:
- For category: map synonyms (e.g., "wireless headphones" -> could be earbuds or headset, "phone" -> smartphone)
- For price: "under X" means price_max = X-1 (strictly less than), "around X" means price_min = X*0.8, price_max = X*1.2
- For use_case: infer from context (e.g., "for coding", "student laptop", "video editing")
- For product_names: extract exact names or partial names mentioned
- For attributes: key specs the user cares about
- Return null for fields that aren't mentioned or can't be inferred

Examples:
- "laptop under 50000 for coding" -> {"category": "laptop", "price_max": 49999, "use_case": "coding", ...}
- "wireless headphones with good battery" -> {"category": null, "attributes": ["wireless", "battery"], ...}
- "Does the NovaBook Air have enough RAM?" -> {"product_names": ["NovaBook Air"], "attributes": ["RAM"], ...}

User query: {query}

Return only valid JSON, no other text."""


def extract_query_info(query: str, llm_client: LLMClient) -> Dict[str, Any]:
    """
    Extract structured information from a natural language query using LLM.
    Falls back to keyword-based extraction if JSON parsing fails.
    
    Args:
        query: User's natural language query
        llm_client: LLM client instance
    
    Returns:
        Dictionary with extracted information
    """
    try:
        # Try LLM-based extraction
        prompt = QUERY_UNDERSTANDING_PROMPT.format(query=query)
        result = llm_client.generate_json("", prompt, temperature=0.0)
        
        # Validate and clean the result
        validated = {
            "category": result.get("category"),
            "price_min": result.get("price_min"),
            "price_max": result.get("price_max"),
            "use_case": result.get("use_case"),
            "product_names": result.get("product_names", []),
            "attributes": result.get("attributes", [])
        }
        
        return validated
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"LLM JSON parsing failed, falling back to keyword extraction: {e}")
        return _keyword_based_extraction(query)
    except Exception as e:
        # Catch any LLM API errors (timeout, rate limit, network)
        print(f"LLM API error, falling back to keyword extraction: {e}")
        return _keyword_based_extraction(query)


def _keyword_based_extraction(query: str) -> Dict[str, Any]:
    """
    Fallback keyword-based extraction when LLM parsing fails.
    
    Args:
        query: User's natural language query
    
    Returns:
        Dictionary with extracted information
    """
    query_lower = query.lower()
    
    # Extract category
    category = None
    category_keywords = {
        "laptop": ["laptop", "notebook"],
        "earbuds": ["earbuds", "earbud", "tws", "true wireless"],
        "headset": ["headset", "headphone", "headphones"],
        "smartphone": ["smartphone", "phone", "mobile"],
        "smartwatch": ["smartwatch", "watch", "fitness band"],
        "tablet": ["tablet", "ipad"],
        "speaker": ["speaker", "bluetooth speaker"],
        "accessories": ["accessory", "accessories", "power bank", "hub", "cable"]
    }
    
    for cat, keywords in category_keywords.items():
        if any(kw in query_lower for kw in keywords):
            category = cat
            break
    
    # Extract price
    price_min = None
    price_max = None
    
    # Match patterns like "under 50000", "under ₹50,000", "below 50k"
    under_match = re.search(r'under|below|less than\s*(?:₹|rs\.?|inr)?\s*(\d+)(?:,(\d+))?(?:k|000)?', query_lower)
    if under_match:
        try:
            price_str = under_match.group(1) if under_match.group(1) else ""
            if under_match.group(2):
                price_str += under_match.group(2)
            
            if price_str:  # Only process if we have a valid string
                price = int(price_str)
                if 'k' in query_lower[under_match.start():under_match.end()]:
                    price *= 1000
                price_max = price - 1  # Strictly under
        except (ValueError, AttributeError):
            pass  # Skip if parsing fails
    
    # Match patterns like "around 50000"
    around_match = re.search(r'around|about\s*(?:₹|rs\.?|inr)?\s*(\d+)(?:,(\d+))?(?:k|000)?', query_lower)
    if around_match:
        try:
            price_str = around_match.group(1) if around_match.group(1) else ""
            if around_match.group(2):
                price_str += around_match.group(2)
            
            if price_str:  # Only process if we have a valid string
                price = int(price_str)
                if 'k' in query_lower[around_match.start():around_match.end()]:
                    price *= 1000
                price_min = int(price * 0.8)
                price_max = int(price * 1.2)
        except (ValueError, AttributeError):
            pass  # Skip if parsing fails
    
    # Extract use case
    use_case = None
    use_case_keywords = {
        "coding": ["coding", "programming", "developer", "development"],
        "video_editing": ["video editing", "editing", "content creation", "creator"],
        "student": ["student", "study", "college", "school"],
        "gaming": ["gaming", "gamer", "game"],
        "music": ["music", "audio", "sound"],
        "general": ["general", "everyday", "basic"]
    }
    
    for uc, keywords in use_case_keywords.items():
        if any(kw in query_lower for kw in keywords):
            use_case = uc
            break
    
    # Extract key attributes mentioned
    attributes = []
    attribute_keywords = ["ram", "battery", "anc", "gpu", "storage", "wireless", "cpu", 
                         "ssd", "camera", "display", "water resistant", "foldable"]
    for attr in attribute_keywords:
        if attr in query_lower:
            attributes.append(attr)
    
    return {
        "category": category,
        "price_min": price_min,
        "price_max": price_max,
        "use_case": use_case,
        "product_names": [],  # Harder to extract reliably with keywords
        "attributes": attributes
    }
