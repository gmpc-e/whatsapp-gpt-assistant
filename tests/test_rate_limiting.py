"""Tests for rate limiting functionality."""

import pytest
import time
from app.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test cases for rate limiting."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.limiter = RateLimiter()
    
    def test_rate_limit_allows_initial_calls(self):
        """Test that initial calls are allowed."""
        assert self.limiter.is_allowed("test_key", 5, 60) is True
        assert self.limiter.is_allowed("test_key", 5, 60) is True
    
    def test_rate_limit_blocks_excess_calls(self):
        """Test that excess calls are blocked."""
        for _ in range(5):
            assert self.limiter.is_allowed("test_key", 5, 60) is True
        
        assert self.limiter.is_allowed("test_key", 5, 60) is False
    
    def test_rate_limit_resets_after_window(self):
        """Test that rate limit resets after time window."""
        for _ in range(3):
            assert self.limiter.is_allowed("test_key", 3, 1) is True
        
        assert self.limiter.is_allowed("test_key", 3, 1) is False
        
        time.sleep(1.1)
        
        assert self.limiter.is_allowed("test_key", 3, 1) is True
    
    def test_rate_limit_different_keys(self):
        """Test that different keys have separate limits."""
        for _ in range(3):
            assert self.limiter.is_allowed("key1", 3, 60) is True
        
        assert self.limiter.is_allowed("key1", 3, 60) is False
        
        assert self.limiter.is_allowed("key2", 3, 60) is True
    
    def test_wait_time_calculation(self):
        """Test wait time calculation."""
        for _ in range(3):
            assert self.limiter.is_allowed("test_key", 3, 10) is True
        
        wait_time = self.limiter.wait_time("test_key", 3, 10)
        assert 0 < wait_time <= 10
