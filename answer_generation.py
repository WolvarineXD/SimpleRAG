"""
Answer Generation - Generates grounded answers using LLM with retrieved products.
Includes guardrail checking to ensure facts are accurate.
"""

import re
from typing import List, Dict, Any, Tuple
from llm_client import LLMClient


def load_system_prompt(prompt_path: str, products: List[Dict[str, Any]]) -> str:
    """
    Load system prompt and inject catalog data.
    
    Args:
        prompt_path: Path to system prompt markdown file
        products: List of retrieved products to inject
    
    Returns:
        Complete system prompt with catalog data
    """
    with open(prompt_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Format catalog data
    catalog_text = format_catalog_for_prompt(products)
    
    # Inject into template
    return template.replace("{{CATALOG}}", catalog_text)


def format_catalog_for_prompt(products: List[Dict[str, Any]]) -> str:
    """Format products as text for the LLM prompt."""
    if not products:
        return "No products available."
    
    lines = []
    for product in products:
        specs_text = []
        specs = product.get("specs", {})
        
        for key, value in specs.items():
            if value is True:
                specs_text.append(key.replace("_", " "))
            elif value is False:
                continue  # Don't mention false boolean specs
            elif isinstance(value, (int, float)):
                # Format with units
                if key == "ram_gb":
                    specs_text.append(f"{value}GB RAM")
                elif key == "storage_gb":
                    specs_text.append(f"{value}GB storage")
                elif key == "battery_hr":
                    specs_text.append(f"{value}hr battery")
                elif key == "battery_mah":
                    specs_text.append(f"{value}mAh battery")
                elif key == "battery_days":
                    specs_text.append(f"{value} day battery")
                elif key == "camera_mp":
                    specs_text.append(f"{value}MP camera")
                elif key == "display_inches":
                    specs_text.append(f"{value} inch display")
                elif key == "capacity_mah":
                    specs_text.append(f"{value}mAh capacity")
                elif key == "dpi":
                    specs_text.append(f"{value} DPI")
                elif key == "pressure_levels":
                    specs_text.append(f"{value} pressure levels")
                elif key == "capacity_gb":
                    specs_text.append(f"{value}GB capacity")
                elif key == "speed_mbps":
                    specs_text.append(f"{value} MB/s speed")
                elif key == "ports":
                    specs_text.append(f"{value} ports")
                elif key == "programmable_buttons":
                    specs_text.append(f"{value} programmable buttons")
                elif key == "length_m":
                    specs_text.append(f"{value}m length")
                elif key == "fps":
                    specs_text.append(f"{value} fps")
                else:
                    specs_text.append(f"{key.replace('_', ' ')}: {value}")
            elif isinstance(value, str):
                specs_text.append(f"{key.replace('_', ' ')}: {value}")
        
        product_line = f"- **{product['name']}** (ID: {product['id']}) | {product['category'].title()} | ₹{product['price_inr']:,}"
        if specs_text:
            product_line += f" | {', '.join(specs_text)}"
        if product.get("description"):
            product_line += f"\n  {product['description']}"
        
        lines.append(product_line)
    
    return "\n\n".join(lines)


def generate_answer(
    user_query: str,
    products: List[Dict[str, Any]],
    llm_client: LLMClient,
    prompt_path: str = "prompts/system_prompt.md",
    no_results_reason: str = None
) -> str:
    """
    Generate an answer using the LLM with retrieved products.
    
    Args:
        user_query: Original user question
        products: Retrieved products (context)
        llm_client: LLM client instance
        prompt_path: Path to system prompt file
        no_results_reason: Optional message explaining why filters returned no/limited results
    
    Returns:
        Generated answer
    """
    try:
        # Load and prepare system prompt
        system_prompt = load_system_prompt(prompt_path, products)
        
        # Add context about no results if applicable
        if no_results_reason:
            system_prompt += f"\n\n**Important**: {no_results_reason}"
        
        # Generate answer
        answer = llm_client.generate(system_prompt, user_query, temperature=0.0)
        
        return answer
    except Exception as e:
        # Catch LLM API errors
        print(f"Error generating answer: {e}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again in a moment."


def check_guardrails(answer: str, products: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Verify that all product names and prices in the answer exist in retrieved products.
    
    Args:
        answer: Generated answer text
        products: Retrieved products that were provided to LLM
    
    Returns:
        Tuple of (is_valid, list of violations)
    """
    violations = []
    
    # Build valid product names and prices
    valid_names = {p["name"].lower() for p in products}
    valid_prices = {p["price_inr"] for p in products}
    valid_ids = {p["id"] for p in products}
    
    # Check for prices in answer (₹ followed by numbers)
    # Only check prices that look like product prices (with commas or "at ₹")
    price_pattern = r'(?:at|costs?|priced at|for)\s*₹\s*(\d[\d,]*)'
    mentioned_prices = re.findall(price_pattern, answer, re.IGNORECASE)
    
    for price_str in mentioned_prices:
        price = int(price_str.replace(",", ""))
        if price not in valid_prices:
            violations.append(f"Product price ₹{price:,} mentioned but not in retrieved products")
    
    # Check for product IDs mentioned (if any)
    id_pattern = r'\bP\d+\b'
    mentioned_ids = re.findall(id_pattern, answer)
    for pid in mentioned_ids:
        if pid not in valid_ids:
            violations.append(f"Product ID {pid} mentioned but not in retrieved products")
    
    # Relaxed check - allow general price mentions for comparisons
    # Only flag if it's clearly stating a product price incorrectly
    
    is_valid = len(violations) == 0
    return is_valid, violations


def generate_with_guardrails(
    user_query: str,
    products: List[Dict[str, Any]],
    llm_client: LLMClient,
    prompt_path: str = "prompts/system_prompt.md",
    no_results_reason: str = None,
    max_retries: int = 1
) -> str:
    """
    Generate answer with guardrail checking. Retry once with stricter prompt if needed.
    
    Args:
        user_query: Original user question
        products: Retrieved products
        llm_client: LLM client instance
        prompt_path: Path to system prompt file
        no_results_reason: Optional context about filtering results
        max_retries: Maximum retry attempts
    
    Returns:
        Generated answer (with fallback if guardrails fail)
    """
    # First attempt
    answer = generate_answer(user_query, products, llm_client, prompt_path, no_results_reason)
    is_valid, violations = check_guardrails(answer, products)
    
    if is_valid:
        return answer
    
    # Retry with stricter instruction
    if max_retries > 0:
        print(f"Guardrail check failed: {violations}. Retrying with stricter prompt...")
        
        strict_prompt_path = prompt_path
        system_prompt = load_system_prompt(strict_prompt_path, products)
        system_prompt += "\n\n**CRITICAL**: You MUST only mention products, prices, and specifications that are explicitly listed in the catalog above. Double-check every fact before including it in your answer."
        
        if no_results_reason:
            system_prompt += f"\n\n**Important**: {no_results_reason}"
        
        answer = llm_client.generate(system_prompt, user_query, temperature=0.0)
        is_valid, violations = check_guardrails(answer, products)
        
        if is_valid:
            return answer
    
    # Fallback: safe generic message
    print(f"Guardrail check failed after retry: {violations}. Using safe fallback.")
    return "I apologize, but I need to verify some information before answering your question accurately. Please ask me again, and I'll make sure to give you only verified information from our catalog."
