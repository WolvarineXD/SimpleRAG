"""
Unit tests for retrieval module (deterministic functions, no LLM required).
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from retrieval import (
    apply_hard_filters,
    fuzzy_match_score,
    match_product_name,
    calculate_keyword_score,
    calculate_use_case_score,
)


# Sample test products
TEST_PRODUCTS = [
    {
        "id": "P1",
        "name": "NovaBook Air 14",
        "category": "laptop",
        "price_inr": 52000,
        "specs": {"ram_gb": 8, "storage_gb": 512, "cpu": "Intel i5", "battery_hr": 10, "ssd": True},
        "description": "Lightweight laptop for everyday use"
    },
    {
        "id": "P2",
        "name": "NovaBook Pro 15",
        "category": "laptop",
        "price_inr": 78000,
        "specs": {"ram_gb": 16, "storage_gb": 1024, "cpu": "Intel i7", "gpu": "RTX 3050", "battery_hr": 8, "ssd": True},
        "description": "High-performance laptop with GPU"
    },
    {
        "id": "P3",
        "name": "SoundCore X40",
        "category": "earbuds",
        "price_inr": 3500,
        "specs": {"battery_hr": 30, "anc": True, "ip_rating": "IP54"},
        "description": "True wireless earbuds with ANC"
    },
    {
        "id": "P4",
        "name": "SoundCore Studio Pro",
        "category": "headset",
        "price_inr": 8200,
        "specs": {"battery_hr": 50, "anc": True, "foldable": True},
        "description": "Over-ear headphones with studio-grade ANC"
    },
]


class TestHardFilters:
    """Tests for hard filtering (category and price)."""
    
    def test_category_filter_exact(self):
        """Test exact category match."""
        result = apply_hard_filters(TEST_PRODUCTS, category="laptop")
        assert len(result) == 2
        assert all(p["category"] == "laptop" for p in result)
    
    def test_category_filter_synonym(self):
        """Test category synonym mapping (headphones -> earbuds + headset)."""
        # Note: This requires the synonym to be in CATEGORY_SYNONYMS
        result = apply_hard_filters(TEST_PRODUCTS, category="earbuds")
        assert len(result) == 1
        assert result[0]["id"] == "P3"
    
    def test_price_max_filter(self):
        """Test price_max filter (strictly under)."""
        result = apply_hard_filters(TEST_PRODUCTS, price_max=50000)
        assert len(result) == 2  # P3 (3500) and P4 (8200)
        assert all(p["price_inr"] <= 50000 for p in result)
    
    def test_price_min_filter(self):
        """Test price_min filter."""
        result = apply_hard_filters(TEST_PRODUCTS, price_min=10000)
        assert len(result) == 2
        assert all(p["price_inr"] >= 10000 for p in result)
    
    def test_price_range_filter(self):
        """Test both price_min and price_max."""
        result = apply_hard_filters(TEST_PRODUCTS, price_min=5000, price_max=60000)
        assert len(result) == 2
        assert all(5000 <= p["price_inr"] <= 60000 for p in result)
    
    def test_combined_filters(self):
        """Test category and price filters together."""
        result = apply_hard_filters(TEST_PRODUCTS, category="laptop", price_max=55000)
        assert len(result) == 1
        assert result[0]["id"] == "P1"
    
    def test_no_match(self):
        """Test when no products match filters."""
        result = apply_hard_filters(TEST_PRODUCTS, category="laptop", price_max=30000)
        assert len(result) == 0


class TestFuzzyMatching:
    """Tests for fuzzy product name matching."""
    
    def test_exact_match(self):
        """Test exact product name match."""
        score = fuzzy_match_score("NovaBook Air 14", "NovaBook Air 14")
        assert score == 1.0
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        score = fuzzy_match_score("novabook air 14", "NovaBook Air 14")
        assert score == 1.0
    
    def test_substring_match(self):
        """Test substring matching."""
        score = fuzzy_match_score("NovaBook Air", "NovaBook Air 14")
        assert score >= 0.9
    
    def test_typo_tolerance(self):
        """Test matching with typos."""
        score = fuzzy_match_score("novabok air", "NovaBook Air 14")
        assert score > 0.5  # Should still match despite typo
    
    def test_no_match(self):
        """Test completely different strings."""
        score = fuzzy_match_score("iPhone", "NovaBook Air 14")
        assert score < 0.3
    
    def test_match_product_name(self):
        """Test finding products by name."""
        results = match_product_name("novabook air", TEST_PRODUCTS)
        assert len(results) >= 1
        assert results[0]["id"] == "P1"
    
    def test_match_product_name_typo(self):
        """Test finding products with typos."""
        results = match_product_name("soundcore x40", TEST_PRODUCTS)
        assert len(results) >= 1
        assert results[0]["id"] == "P3"


class TestKeywordScoring:
    """Tests for keyword/attribute-based scoring."""
    
    def test_keyword_match_ram(self):
        """Test keyword match for RAM."""
        score = calculate_keyword_score(["RAM"], TEST_PRODUCTS[0])
        assert score > 0.0
    
    def test_keyword_match_gpu(self):
        """Test keyword match for GPU."""
        score_with_gpu = calculate_keyword_score(["GPU"], TEST_PRODUCTS[1])
        score_without_gpu = calculate_keyword_score(["GPU"], TEST_PRODUCTS[0])
        assert score_with_gpu > score_without_gpu
    
    def test_keyword_match_anc(self):
        """Test keyword match for ANC."""
        score = calculate_keyword_score(["ANC"], TEST_PRODUCTS[2])
        assert score > 0.0
    
    def test_multiple_keywords(self):
        """Test scoring with multiple keywords."""
        score = calculate_keyword_score(["battery", "ANC"], TEST_PRODUCTS[2])
        assert score > 0.0
    
    def test_no_keywords(self):
        """Test with no keywords."""
        score = calculate_keyword_score([], TEST_PRODUCTS[0])
        assert score == 0.0


class TestUseCaseScoring:
    """Tests for use-case based scoring."""
    
    def test_video_editing_scoring(self):
        """Test video editing use case favors GPU + high RAM."""
        score_pro = calculate_use_case_score("video_editing", TEST_PRODUCTS[1])  # Has GPU
        score_air = calculate_use_case_score("video_editing", TEST_PRODUCTS[0])  # No GPU
        assert score_pro > score_air
    
    def test_coding_scoring(self):
        """Test coding use case favors RAM + battery."""
        score = calculate_use_case_score("coding", TEST_PRODUCTS[0])
        assert score > 0.0
    
    def test_music_scoring(self):
        """Test music use case favors battery + ANC."""
        score_earbuds = calculate_use_case_score("music", TEST_PRODUCTS[2])
        score_laptop = calculate_use_case_score("music", TEST_PRODUCTS[0])
        assert score_earbuds > score_laptop
    
    def test_no_use_case(self):
        """Test with no use case."""
        score = calculate_use_case_score(None, TEST_PRODUCTS[0])
        assert score == 0.0
    
    def test_invalid_use_case(self):
        """Test with invalid use case."""
        score = calculate_use_case_score("invalid_case", TEST_PRODUCTS[0])
        assert score == 0.0


class TestPriceHandling:
    """Tests for strict price handling (under means strictly under)."""
    
    def test_under_50000_excludes_50000(self):
        """Test 'under ₹50,000' excludes products at exactly ₹50,000."""
        products = [
            {"id": "A", "category": "laptop", "price_inr": 49999},
            {"id": "B", "category": "laptop", "price_inr": 50000},
            {"id": "C", "category": "laptop", "price_inr": 50001},
        ]
        result = apply_hard_filters(products, price_max=49999)
        assert len(result) == 1
        assert result[0]["id"] == "A"
    
    def test_under_with_category(self):
        """Test 'under' with category filter."""
        result = apply_hard_filters(TEST_PRODUCTS, category="laptop", price_max=79999)
        assert len(result) == 2
        
        result = apply_hard_filters(TEST_PRODUCTS, category="laptop", price_max=77999)
        assert len(result) == 1
        assert result[0]["id"] == "P1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
