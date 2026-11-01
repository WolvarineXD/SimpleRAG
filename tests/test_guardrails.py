"""
Unit tests for guardrail checking (no LLM required).
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from answer_generation import check_guardrails


# Sample test products
TEST_PRODUCTS = [
    {
        "id": "P1",
        "name": "NovaBook Air 14",
        "category": "laptop",
        "price_inr": 52000,
        "specs": {"ram_gb": 8},
        "description": "Lightweight laptop"
    },
    {
        "id": "P2",
        "name": "NovaBook Pro 15",
        "category": "laptop",
        "price_inr": 78000,
        "specs": {"ram_gb": 16, "gpu": "RTX 3050"},
        "description": "High-performance laptop"
    },
]


class TestGuardrailChecking:
    """Tests for guardrail validation."""
    
    def test_valid_answer_with_correct_price(self):
        """Test valid answer with correct price."""
        answer = "The NovaBook Air 14 costs ₹52,000."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid
        assert len(violations) == 0
    
    def test_invalid_answer_with_wrong_price(self):
        """Test invalid answer with invented price."""
        answer = "The NovaBook Air 14 costs ₹45,000."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert not is_valid
        assert len(violations) > 0
    
    def test_valid_answer_multiple_prices(self):
        """Test valid answer with multiple correct prices."""
        answer = "The NovaBook Air 14 costs ₹52,000 and the NovaBook Pro 15 costs ₹78,000."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid
    
    def test_invalid_answer_one_wrong_price(self):
        """Test invalid answer with one wrong price."""
        answer = "The NovaBook Air 14 costs ₹52,000 and the NovaBook Pro 15 costs ₹70,000."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert not is_valid
    
    def test_valid_answer_with_product_id(self):
        """Test valid answer mentioning product ID."""
        answer = "Check out P1 for a great laptop."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid
    
    def test_invalid_answer_with_wrong_product_id(self):
        """Test invalid answer with non-existent product ID."""
        answer = "Check out P99 for a great laptop."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert not is_valid
    
    def test_valid_answer_no_price_mentioned(self):
        """Test valid answer without mentioning prices."""
        answer = "The NovaBook Air 14 is a great lightweight laptop."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid
    
    def test_valid_answer_not_in_catalog(self):
        """Test valid answer saying product not in catalog."""
        answer = "We don't have the iPhone 15 in our catalog."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid
    
    def test_price_format_with_spaces(self):
        """Test price format with spaces."""
        answer = "The laptop costs ₹ 52,000."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid
    
    def test_price_format_without_commas(self):
        """Test price format without commas."""
        answer = "The laptop costs ₹52000."
        is_valid, violations = check_guardrails(answer, TEST_PRODUCTS)
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
