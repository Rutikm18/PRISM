# global_price_aggregator.py
import asyncio
import httpx
import time
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from dataclasses import asdict
import logging

# Import configuration
from config_global_price import MARKETPLACE_CONFIGS, RATE_LIMITS, CACHE_CONFIG

# Import all scrapers
from marketplace_apis import (
    AmazonScraper, 
    EbayScraper, 
    WalmartScraper, 
    FlipkartScraper, 
    TargetScraper,
    PriceResult
)

logger = logging.getLogger(__name__)

class HighPerformanceCache:
    """Ultra-fast in-memory cache with TTL"""
    
    def __init__(self, max_size: int = 5000, default_ttl: int = 1800):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    def _is_expired(self, key: str) -> bool:
        if key not in self.cache:
            return True
        
        entry_time, _ = self.cache[key]
        return time.time() - entry_time > self.default_ttl
    
    def get(self, key: str) -> Any:
        if self._is_expired(key):
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return None
        
        self.access_times[key] = time.time()
        _, value = self.cache[key]
        return value
    
    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            # Remove least recently accessed items
            old_keys = sorted(self.access_times.items(), key=lambda x: x[1])[:50]
            for old_key, _ in old_keys:
                self.cache.pop(old_key, None)
                self.access_times.pop(old_key, None)
        
        self.cache[key] = (time.time(), value)
        self.access_times[key] = time.time()

class GlobalPriceAggregator:
    """High-performance global price aggregation system using pure web scraping"""
    
    def __init__(self):
        # Initialize all scrapers
        self.amazon_scraper = AmazonScraper()
        self.ebay_scraper = EbayScraper()
        self.walmart_scraper = WalmartScraper()
        self.flipkart_scraper = FlipkartScraper()
        self.target_scraper = TargetScraper()
        
        self.cache = HighPerformanceCache()
        
        # HTTP client settings for better performance
        self.client_limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.client_timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def get_all_prices(self, query: str, country: str) -> List[Dict[str, Any]]:
        """Get prices from all available marketplaces for a country"""
        
        # Check cache first
        cache_key = hashlib.md5(f"{query}_{country}".encode()).hexdigest()
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {query} in {country}")
            return cached_result
        
        # Create HTTP client with optimized settings
        async with httpx.AsyncClient(
            limits=self.client_limits,
            timeout=self.client_timeout,
            follow_redirects=True,
            http2=False
        ) as client:
            
            # Get available marketplaces for country
            marketplaces = MARKETPLACE_CONFIGS.get(country, {})
            
            # Create async tasks for all available scrapers
            tasks = []
            
            if 'amazon' in marketplaces:
                tasks.append(self.amazon_scraper.search_products(query, country, client))
            
            if 'ebay' in marketplaces:
                tasks.append(self.ebay_scraper.search_products(query, country, client))
            
            if 'walmart' in marketplaces:
                tasks.append(self.walmart_scraper.search_products(query, country, client))
            
            if 'flipkart' in marketplaces:
                tasks.append(self.flipkart_scraper.search_products(query, country, client))
            
            if 'target' in marketplaces:
                tasks.append(self.target_scraper.search_products(query, country, client))
            
            # Execute all tasks concurrently with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=45.0  # Total timeout for all scrapers
                )
                
                # Flatten and filter results
                all_results = []
                for result in results:
                    if isinstance(result, list):
                        all_results.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Scraper task failed: {result}")
                
                # Remove duplicates based on title similarity
                unique_results = self._remove_duplicates(all_results)
                
                # Sort by price and convert to dict
                sorted_results = sorted(unique_results, key=lambda x: x.price)
                final_results = [asdict(result) for result in sorted_results]
                
                # Cache results
                self.cache.set(cache_key, final_results)
                
                logger.info(f"Found {len(final_results)} products for '{query}' in {country}")
                return final_results
            
            except asyncio.TimeoutError:
                logger.error(f"Timeout error for query '{query}' in {country}")
                return []
            except Exception as e:
                logger.error(f"Error in price aggregation: {e}")
                return []
    
    def _remove_duplicates(self, results: List[PriceResult]) -> List[PriceResult]:
        """Remove duplicate products based on title similarity"""
        if not results:
            return []
        
        unique_results = []
        seen_titles = set()
        
        for result in results:
            # Create a normalized title for comparison
            title_normalized = ''.join(result.title.lower().split())[:50]
            
            # Check if we've seen a very similar title
            is_duplicate = False
            for seen_title in seen_titles:
                if self._similarity_ratio(title_normalized, seen_title) > 0.85:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
                seen_titles.add(title_normalized)
        
        return unique_results
    
    def _similarity_ratio(self, a: str, b: str) -> float:
        """Calculate similarity ratio between two strings"""
        if not a or not b:
            return 0.0
        
        # Simple character-based similarity
        common_chars = sum(1 for c in a if c in b)
        return common_chars / max(len(a), len(b))
    
    async def get_prices_multiple_countries(self, query: str, countries: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get prices from multiple countries concurrently"""
        
        # Limit concurrent country searches to avoid overwhelming
        semaphore = asyncio.Semaphore(3)  # Max 3 countries at once
        
        async def search_country(country):
            async with semaphore:
                return await self.get_all_prices(query, country)
        
        try:
            tasks = [search_country(country) for country in countries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions and create result dict
            country_results = {}
            for country, result in zip(countries, results):
                if isinstance(result, Exception):
                    logger.error(f"Error searching in {country}: {result}")
                    country_results[country] = []
                else:
                    country_results[country] = result
            
            return country_results
        
        except Exception as e:
            logger.error(f"Error in multi-country search: {e}")
            return {country: [] for country in countries}
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache.cache),
            'max_size': self.cache.max_size,
            'ttl_seconds': self.cache.default_ttl
        }
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache.cache.clear()
        self.cache.access_times.clear()
        logger.info("Cache cleared")