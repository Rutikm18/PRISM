#!/usr/bin/env python3
"""
Universal Price Comparison Tool
Web scraping and price comparison application with AI-powered product matching.
"""

import threading
import concurrent.futures
import requests
import json
import re
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus, urlparse
from datetime import datetime, timedelta
import hashlib
import os
from pathlib import Path
import random
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_tool.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProductResult:
    """Product search result data structure"""
    link: str
    price: str
    currency: str
    productName: str
    website: str
    availability: str = "In Stock"
    rating: Optional[str] = None
    reviews: Optional[str] = None
    shipping: Optional[str] = None
    seller: Optional[str] = None
    image_url: Optional[str] = None
    discount: Optional[str] = None
    original_price: Optional[str] = None
    relevance_score: float = 0.0
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CacheManager:
    """SQLite-based caching system for search results"""
    
    def __init__(self, cache_duration_minutes: int = 30):
        self.cache_duration = timedelta(minutes=cache_duration_minutes)
        self.db_path = "price_cache.db"
        self._init_db()
    
    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        data TEXT,
                        timestamp TEXT
                    )
                """)
        except Exception as e:
            logger.warning(f"Cache DB initialization failed: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT data, timestamp FROM cache WHERE key = ?", (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    data, timestamp_str = result
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    if datetime.now() - timestamp < self.cache_duration:
                        return json.loads(data)
                    else:
                        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        
        return None
    
    def set(self, key: str, data: Any):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data, timestamp) VALUES (?, ?, ?)",
                    (key, json.dumps(data), datetime.now().isoformat())
                )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

class CountryWebsiteMapper:
    """Maps countries to their popular e-commerce websites"""
    
    WEBSITE_MAP = {
        "US": [
            {"domain": "amazon.com", "priority": 1, "type": "marketplace"},
            {"domain": "walmart.com", "priority": 2, "type": "retail"},
            {"domain": "bestbuy.com", "priority": 3, "type": "electronics"},
            {"domain": "target.com", "priority": 4, "type": "retail"},
            {"domain": "newegg.com", "priority": 5, "type": "electronics"},
            {"domain": "bhphotovideo.com", "priority": 6, "type": "electronics"},
            {"domain": "costco.com", "priority": 7, "type": "wholesale"},
            {"domain": "ebay.com", "priority": 8, "type": "marketplace"}
        ],
        "IN": [
            {"domain": "amazon.in", "priority": 1, "type": "marketplace"},
            {"domain": "flipkart.com", "priority": 2, "type": "marketplace"},
            {"domain": "snapdeal.com", "priority": 3, "type": "marketplace"},
            {"domain": "croma.com", "priority": 4, "type": "electronics"},
            {"domain": "reliancedigital.in", "priority": 5, "type": "electronics"},
            {"domain": "sangeethamobiles.com", "priority": 6, "type": "mobiles"},
            {"domain": "poorvika.com", "priority": 7, "type": "mobiles"},
            {"domain": "vijaysales.com", "priority": 8, "type": "electronics"}
        ],
        "UK": [
            {"domain": "amazon.co.uk", "priority": 1, "type": "marketplace"},
            {"domain": "currys.co.uk", "priority": 2, "type": "electronics"},
            {"domain": "argos.co.uk", "priority": 3, "type": "retail"},
            {"domain": "johnlewis.com", "priority": 4, "type": "retail"},
            {"domain": "very.co.uk", "priority": 5, "type": "retail"},
            {"domain": "ao.com", "priority": 6, "type": "appliances"}
        ],
        "CA": [
            {"domain": "amazon.ca", "priority": 1, "type": "marketplace"},
            {"domain": "bestbuy.ca", "priority": 2, "type": "electronics"},
            {"domain": "canadacomputers.com", "priority": 3, "type": "computers"},
            {"domain": "newegg.ca", "priority": 4, "type": "electronics"},
            {"domain": "walmart.ca", "priority": 5, "type": "retail"}
        ],
        "AU": [
            {"domain": "amazon.com.au", "priority": 1, "type": "marketplace"},
            {"domain": "jbhifi.com.au", "priority": 2, "type": "electronics"},
            {"domain": "harveynorman.com.au", "priority": 3, "type": "electronics"},
            {"domain": "officeworks.com.au", "priority": 4, "type": "office"},
            {"domain": "kogan.com", "priority": 5, "type": "online"}
        ]
    }
    
    @classmethod
    def get_websites_for_country(cls, country: str, limit: int = 5) -> List[Dict[str, Any]]:
        websites = cls.WEBSITE_MAP.get(country.upper(), cls.WEBSITE_MAP["US"])
        return sorted(websites, key=lambda x: x["priority"])[:limit]

class EnhancedWebScraper:
    """Web scraper with rate limiting and error handling"""
    
    def __init__(self):
        self.session = requests.Session()
        self.rate_limiter = {}
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59'
        ]
        
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
    
    def _should_rate_limit(self, domain: str) -> bool:
        """Check if we should rate limit requests to avoid being blocked"""
        now = time.time()
        
        if domain not in self.rate_limiter:
            self.rate_limiter[domain] = []
        
        # Keep only requests from last 60 seconds
        self.rate_limiter[domain] = [
            timestamp for timestamp in self.rate_limiter[domain] 
            if now - timestamp < 60
        ]
        
        # Limit to 10 requests per minute per domain
        if len(self.rate_limiter[domain]) >= 10:
            return True
        
        self.rate_limiter[domain].append(now)
        return False
    
    def fetch_page(self, url: str, timeout: int = 15) -> Optional[str]:
        """Fetch web page with error handling and rate limiting"""
        try:
            domain = urlparse(url).netloc
            
            if self._should_rate_limit(domain):
                logger.warning(f"Rate limiting {domain}")
                return None
            
            # Random user agent and delay
            self.session.headers['User-Agent'] = random.choice(self.user_agents)
            time.sleep(random.uniform(0.5, 2.0))
            
            response = self.session.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                logger.warning(f"Rate limited by {domain}")
                time.sleep(5)
                return None
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            return None

class EnhancedProductParser:
    """Extracts product information from HTML using site-specific selectors"""
    
    SITE_SELECTORS = {
        "amazon": {
            "title": ["#productTitle", "h1.a-size-large", ".product-title", "h1[data-automation-id='product-title']", ".a-color-base.a-text-normal"],
            "price": ["span.a-price-whole", ".a-price .a-offscreen", ".a-price-range", ".a-price.a-text-price.a-size-medium.a-color-base .a-offscreen", ".a-price-current"],
            "original_price": [".a-price.a-text-price .a-offscreen", ".a-price-list-price .a-offscreen"],
            "availability": ["#availability span", ".a-color-success", ".a-color-error", "#availability .a-color-state"],
            "rating": ["span.a-icon-alt", ".a-icon-alt", ".a-declarative .a-icon-alt"],
            "reviews": ["#acrCustomerReviewText", ".a-link-normal .a-size-base"]
        },
        "walmart": {
            "title": ["h1[data-testid='product-title']", "h1.prod-ProductTitle", "h1[data-automation-id='product-title']"],
            "price": ["span[data-testid='price-current']", ".price-current", "[data-automation-id='product-price'] span"],
            "availability": ["div[data-testid='fulfillment-speed']", ".fulfillment-speed"],
            "rating": ["span.average-rating", ".rating-number"]
        },
        "flipkart": {
            "title": ["span.B_NuCI", "h1.yhB1nd", ".B_NuCI"],
            "price": ["div._30jeq3._16Jk6d", "div._1_WHN1", "._30jeq3"],
            "availability": ["div._16FRp0", ".availability"],
            "rating": ["div._3LWZlK", ".rating-div"]
        },
        "bestbuy": {
            "title": ["h1.sr-only", "h1.heading-5", ".sku-title h1"],
            "price": ["span.sr-only", ".pricing-price__range", ".current-price .sr-only"],
            "availability": ["div.fulfillment-add-to-cart-button", ".availability"]
        }
    }
    
    def __init__(self):
        self.currency_symbols = {
            "US": "$", "IN": "₹", "UK": "£", "CA": "C$", "AU": "A$",
            "DE": "€", "FR": "€", "JP": "¥", "SG": "S$", "BR": "R$"
        }
    
    def extract_site_type(self, url: str) -> str:
        """Determine website type from URL"""
        url_lower = url.lower()
        if "amazon" in url_lower:
            return "amazon"
        elif "walmart" in url_lower:
            return "walmart"
        elif "flipkart" in url_lower:
            return "flipkart"
        elif "bestbuy" in url_lower:
            return "bestbuy"
        else:
            return "generic"
    
    def parse_product_page(self, html: str, url: str, country: str) -> Optional[ProductResult]:
        """Extract product information from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            site_type = self.extract_site_type(url)
            selectors = self.SITE_SELECTORS.get(site_type, {})
            
            title = self._extract_text(soup, selectors.get("title", [])) or self._extract_title_fallback(soup)
            price = self._extract_price(soup, selectors.get("price", [])) or self._extract_price_fallback(soup)
            original_price = self._extract_price(soup, selectors.get("original_price", []))
            currency = self._get_currency_for_country(country)
            availability = self._extract_text(soup, selectors.get("availability", [])) or "Unknown"
            rating = self._extract_text(soup, selectors.get("rating", []))
            reviews = self._extract_text(soup, selectors.get("reviews", []))
            image_url = self._extract_image(soup, selectors.get("image", []))
            
            discount = self._calculate_discount(price, original_price) if original_price else None
            
            if title and price:
                return ProductResult(
                    link=url,
                    price=price,
                    currency=currency,
                    productName=title,
                    website=self._extract_domain(url),
                    availability=availability,
                    rating=rating,
                    reviews=reviews,
                    image_url=image_url,
                    discount=discount,
                    original_price=original_price
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing product page {url}: {e}")
            return None
    
    def _extract_text(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Try multiple selectors to extract text"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    text = text.replace('\n', ' ').replace('\r', '')
                    return text.strip()
            except Exception:
                continue
        return ""
    
    def _extract_price(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract price using multiple patterns"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text(strip=True)
                    patterns = [
                        r'[\d,]+\.?\d*',
                        r'\$[\d,]+\.?\d*',
                        r'₹[\d,]+\.?\d*',
                        r'£[\d,]+\.?\d*',
                        r'€[\d,]+\.?\d*'
                    ]
                    
                    for pattern in patterns:
                        price_match = re.search(pattern, price_text.replace(',', ''))
                        if price_match:
                            return re.sub(r'[^\d.]', '', price_match.group())
            except Exception:
                continue
        return ""
    
    def _extract_title_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback title extraction"""
        fallback_selectors = ["h1", "title", ".product-name", ".item-title", "[data-testid*='title']", "[class*='title']"]
        return self._extract_text(soup, fallback_selectors)
    
    def _extract_price_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback price extraction"""
        fallback_selectors = ["[class*='price']", "[data-testid*='price']", ".cost", ".amount", ".value"]
        return self._extract_price(soup, fallback_selectors)
    
    def _extract_image(self, soup: BeautifulSoup, selectors: List[str]) -> str:
        """Extract product image URL"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    return element.get('src', '') or element.get('data-src', '')
            except Exception:
                continue
        return ""
    
    def _calculate_discount(self, current_price: str, original_price: str) -> Optional[str]:
        """Calculate discount percentage"""
        try:
            current = float(re.sub(r'[^\d.]', '', current_price))
            original = float(re.sub(r'[^\d.]', '', original_price))
            
            if original > current:
                discount_percent = round(((original - current) / original) * 100)
                return f"{discount_percent}%"
        except:
            pass
        return None
    
    def _get_currency_for_country(self, country: str) -> str:
        return self.currency_symbols.get(country.upper(), "$")
    
    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc
        except:
            return ""

class EnhancedSearchEngine:
    """Coordinates concurrent searching across multiple websites"""
    
    def __init__(self):
        self.scraper = EnhancedWebScraper()
        self.parser = EnhancedProductParser()
        self.cache = CacheManager()
    
    def search_products(self, query: str, country: str, max_workers: int = 5) -> List[ProductResult]:
        """Search products across multiple websites concurrently"""
        # Check cache first
        cache_key = hashlib.md5(f"{query}_{country}".encode()).hexdigest()
        cached_results = self.cache.get(cache_key)
        
        if cached_results:
            logger.info(f"Found cached results for {query} in {country}")
            return [ProductResult(**result) for result in cached_results]
        
        websites = CountryWebsiteMapper.get_websites_for_country(country)
        
        # Generate search URLs
        all_urls = []
        for website in websites:
            search_urls = self._generate_search_urls(query, website["domain"])
            all_urls.extend(search_urls)
        
        # Concurrent search
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self._search_single_site, url, country): url 
                for url in all_urls
            }
            
            for future in concurrent.futures.as_completed(future_to_url, timeout=60):
                try:
                    site_results = future.result(timeout=30)
                    if site_results:
                        results.extend(site_results)
                except Exception as e:
                    url = future_to_url[future]
                    logger.error(f"Error processing {url}: {e}")
        
        # Process results
        unique_results = self._remove_duplicates(results)
        sorted_results = self._sort_by_price(unique_results)
        
        # Cache results
        if sorted_results:
            self.cache.set(cache_key, [result.to_dict() for result in sorted_results])
        
        return sorted_results
    
    def _generate_search_urls(self, query: str, website: str) -> List[str]:
        """Generate search URLs for different websites"""
        encoded_query = quote_plus(query)
        urls = []
        
        try:
            if "amazon" in website:
                urls.append(f"https://{website}/s?k={encoded_query}")
            elif "walmart" in website:
                urls.append(f"https://{website}/search?q={encoded_query}")
            elif "flipkart" in website:
                urls.append(f"https://{website}/search?q={encoded_query}")
            elif "bestbuy" in website:
                urls.append(f"https://{website}/site/searchpage.jsp?st={encoded_query}")
            else:
                urls.extend([
                    f"https://{website}/search?q={encoded_query}",
                    f"https://{website}/search?query={encoded_query}",
                    f"https://{website}/products?search={encoded_query}"
                ])
        except Exception as e:
            logger.error(f"Error generating URLs for {website}: {e}")
        
        return urls
    
    def _search_single_site(self, url: str, country: str) -> List[ProductResult]:
        """Search single website and extract products"""
        try:
            html = self.scraper.fetch_page(url)
            if not html:
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            product_links = self._extract_product_links(soup, url)
            
            results = []
            for link in product_links[:3]:  # Limit to top 3 per site
                try:
                    product_html = self.scraper.fetch_page(link)
                    if product_html:
                        product = self.parser.parse_product_page(product_html, link, country)
                        if product:
                            results.append(product)
                except Exception as e:
                    logger.error(f"Error processing product {link}: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching {url}: {e}")
            return []
    
    def _extract_product_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract product links from search results"""
        links = []
        
        link_selectors = [
            'a[href*="/dp/"]', 'a[href*="/product/"]', 'a[href*="/item/"]',
            'a[href*="/p/"]', 'a[href*="/site/"]', 'a[href*="/products/"]',
            '[data-testid*="product"] a', '.product-item a', '.search-result a'
        ]
        
        for selector in link_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    href = element.get('href')
                    if href:
                        if href.startswith('/'):
                            full_url = urljoin(base_url, href)
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            continue
                        
                        unwanted = ['javascript:', 'mailto:', '#', 'tel:']
                        if any(skip in full_url.lower() for skip in unwanted):
                            continue
                        
                        links.append(full_url)
            except Exception:
                continue
        
        unique_links = list(dict.fromkeys(links))
        return unique_links[:10]
    
    def _remove_duplicates(self, results: List[ProductResult]) -> List[ProductResult]:
        """Remove duplicate products"""
        seen = set()
        unique_results = []
        
        for result in results:
            keys = [
                f"{result.productName}_{result.price}_{result.website}",
                f"{result.productName.lower()}_{result.price}",
                f"{result.price}_{result.website}"
            ]
            
            key_exists = any(key in seen for key in keys)
            
            if not key_exists:
                for key in keys:
                    seen.add(key)
                unique_results.append(result)
        
        return unique_results
    
    def _sort_by_price(self, results: List[ProductResult]) -> List[ProductResult]:
        """Sort products by price (lowest first)"""
        def price_key(result):
            try:
                price_num = float(re.sub(r'[^\d.]', '', result.price))
                return price_num
            except:
                return float('inf')
        
        return sorted(results, key=price_key)

class EnhancedAIProductMatcher:
    """AI-powered product relevance matching"""
    
    def __init__(self):
        self.brand_database = {
            'apple': ['iphone', 'ipad', 'macbook', 'airpods', 'apple watch'],
            'samsung': ['galaxy', 'note', 'tab', 'buds'],
            'google': ['pixel', 'nest', 'chromecast'],
            'oneplus': ['nord', 'pro', 'ace'],
            'xiaomi': ['redmi', 'mi', 'poco'],
            'boat': ['airdopes', 'rockerz', 'storm'],
            'sony': ['wh', 'wf', 'playstation'],
            'lg': ['oled', 'nanocell', 'ultragear'],
            'hp': ['pavilion', 'envy', 'omen'],
            'dell': ['inspiron', 'xps', 'alienware'],
            'lenovo': ['thinkpad', 'ideapad', 'legion']
        }
    
    def extract_query_features(self, query: str) -> Dict[str, List[str]]:
        """Extract features from search query for matching"""
        query_lower = query.lower()
        
        # Extract brands and models
        found_brands = []
        brand_models = []
        
        for brand, models in self.brand_database.items():
            if brand in query_lower:
                found_brands.append(brand)
                for model in models:
                    if model in query_lower:
                        brand_models.append(model)
        
        # Extract model patterns
        model_pattern = r'\b([a-zA-Z0-9]+\s?(?:pro|max|plus|mini|ultra|lite|air|se|note|tab|watch)?)\b'
        models = re.findall(model_pattern, query_lower)
        
        # Extract specifications
        spec_patterns = {
            'storage': r'\b(\d+(?:gb|tb|mb))\b',
            'display': r'\b(\d+(?:inch|"|\'|cm))\b',
            'frequency': r'\b(\d+(?:hz|khz|mhz|ghz))\b',
            'camera': r'\b(\d+(?:mp|megapixel))\b',
            'battery': r'\b(\d+(?:mah|wh))\b',
            'ram': r'\b(\d+gb\s*ram|ram\s*\d+gb)\b'
        }
        
        specs = {}
        for spec_type, pattern in spec_patterns.items():
            matches = re.findall(pattern, query_lower)
            if matches:
                specs[spec_type] = matches
        
        # Extract colors
        colors = ['black', 'white', 'silver', 'gold', 'blue', 'red', 'green', 'purple', 'pink', 'gray', 'grey']
        found_colors = [color for color in colors if color in query_lower]
        
        return {
            'brands': found_brands,
            'brand_models': brand_models,
            'models': models,
            'specs': specs,
            'colors': found_colors,
            'keywords': query_lower.split()
        }
    
    def calculate_relevance_score(self, product_name: str, query_features: Dict[str, List[str]]) -> float:
        """Calculate product relevance score (0.0 to 1.0)"""
        product_lower = product_name.lower()
        score = 0.0
        
        # Brand matching (40% weight)
        for brand in query_features['brands']:
            if brand in product_lower:
                score += 0.4
                for model in query_features['brand_models']:
                    if model in product_lower:
                        score += 0.1
        
        # Model matching (30% weight)
        for model in query_features['models']:
            if len(model) > 2 and model in product_lower:
                score += 0.3
        
        # Specification matching (20% weight)
        for spec_type, spec_values in query_features['specs'].items():
            for spec in spec_values:
                if spec in product_lower:
                    score += 0.2
        
        # Color matching (5% weight)
        for color in query_features['colors']:
            if color in product_lower:
                score += 0.05
        
        # Keyword matching (5% weight)
        if query_features['keywords']:
            matched_keywords = sum(1 for keyword in query_features['keywords'] 
                                 if len(keyword) > 2 and keyword in product_lower)
            keyword_ratio = matched_keywords / len(query_features['keywords'])
            score += keyword_ratio * 0.05
        
        return min(score, 1.0)
    
    def filter_relevant_products(self, products: List[ProductResult], query: str, threshold: float = 0.2) -> List[ProductResult]:
        """Filter and sort products by relevance"""
        query_features = self.extract_query_features(query)
        relevant_products = []
        
        for product in products:
            relevance_score = self.calculate_relevance_score(product.productName, query_features)
            product.relevance_score = relevance_score
            
            if relevance_score >= threshold:
                relevant_products.append(product)
        
        # Sort by relevance then price
        relevant_products.sort(key=lambda x: (-x.relevance_score, float(re.sub(r'[^\d.]', '', x.price) or '999999')))
        
        return relevant_products

class PriceComparisonTool:
    """Main price comparison coordinator"""
    
    def __init__(self):
        self.search_engine = EnhancedSearchEngine()
        self.ai_matcher = EnhancedAIProductMatcher()
        self.cache = CacheManager()
    
    def compare_prices(self, country: str, query: str) -> List[Dict[str, Any]]:
        """Main price comparison method"""
        logger.info(f"Searching for '{query}' in {country}")
        
        try:
            raw_results = self.search_engine.search_products(query, country)
            logger.info(f"Found {len(raw_results)} raw results")
            
            relevant_results = self.ai_matcher.filter_relevant_products(raw_results, query)
            logger.info(f"Found {len(relevant_results)} relevant products after AI filtering")
            
            formatted_results = [result.to_dict() for result in relevant_results]
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in price comparison: {e}")
            return []

# Flask Web Application
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

price_tool = PriceComparisonTool()

@app.route('/')
def index():
    """Web interface"""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Universal Price Comparison Tool</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1000px; 
                margin: 0 auto; 
                background: white; 
                padding: 40px; 
                border-radius: 20px; 
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                text-align: center; 
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                text-align: center; 
                color: #666; 
                margin-bottom: 40px;
                font-size: 1.1em;
            }
            .form-group { 
                margin: 25px 0; 
                position: relative;
            }
            label { 
                display: block; 
                margin-bottom: 8px; 
                font-weight: 600;
                color: #444;
                font-size: 1.1em;
            }
            input, select { 
                width: 100%; 
                padding: 15px 20px; 
                border: 2px solid #e0e0e0; 
                border-radius: 10px;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            button { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 15px 30px; 
                border: none; 
                cursor: pointer; 
                border-radius: 10px; 
                font-size: 18px;
                font-weight: 600;
                width: 100%;
                transition: all 0.3s ease;
            }
            button:hover { 
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }
            button:disabled {
                opacity: 0.7;
                cursor: not-allowed;
                transform: none;
            }
            .results { margin-top: 40px; }
            .product { 
                border: 1px solid #e0e0e0; 
                padding: 25px; 
                margin: 15px 0; 
                border-radius: 15px; 
                background: #fafafa;
                transition: all 0.3s ease;
                position: relative;
            }
            .product:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .product-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 15px;
            }
            .product-title {
                font-size: 1.3em;
                font-weight: 600;
                color: #333;
                margin-bottom: 5px;
            }
            .price { 
                font-size: 2em; 
                font-weight: bold; 
                color: #28a745;
                margin-bottom: 10px;
            }
            .original-price {
                text-decoration: line-through;
                color: #888;
                margin-left: 10px;
                font-size: 0.8em;
            }
            .discount {
                background: #ff4757;
                color: white;
                padding: 4px 8px;
                border-radius: 5px;
                font-size: 0.8em;
                margin-left: 10px;
            }
            .product-info {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            .info-item {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .info-item i {
                color: #667eea;
                width: 16px;
            }
            .loading { 
                text-align: center; 
                padding: 40px;
            }
            .spinner { 
                border: 4px solid #f3f3f3; 
                border-top: 4px solid #667eea; 
                border-radius: 50%; 
                width: 50px; 
                height: 50px; 
                animation: spin 1s linear infinite; 
                margin: 20px auto; 
            }
            @keyframes spin { 
                0% { transform: rotate(0deg); } 
                100% { transform: rotate(360deg); } 
            }
            .relevance-score {
                position: absolute;
                top: 15px;
                right: 15px;
                background: #667eea;
                color: white;
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 0.8em;
            }
            .stats {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
            }
            .no-results {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .error {
                background: #ffe6e6;
                color: #d63031;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 4px solid #d63031;
            }
            @media (max-width: 768px) {
                .container { padding: 20px; }
                h1 { font-size: 2em; }
                .product-header { flex-direction: column; }
                .product-info { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1><i class="fas fa-shopping-cart"></i> Universal Price Comparison Tool</h1>
            <p class="subtitle">Find the best prices across multiple websites worldwide with AI-powered matching</p>
            
            <form id="searchForm">
                <div class="form-group">
                    <label for="country"><i class="fas fa-globe"></i> Country</label>
                    <select id="country" name="country">
                        <option value="US">🇺🇸 United States</option>
                        <option value="IN">🇮🇳 India</option>
                        <option value="UK">🇬🇧 United Kingdom</option>
                        <option value="CA">🇨🇦 Canada</option>
                        <option value="AU">🇦🇺 Australia</option>
                        <option value="DE">🇩🇪 Germany</option>
                        <option value="FR">🇫🇷 France</option>
                        <option value="JP">🇯🇵 Japan</option>
                        <option value="SG">🇸🇬 Singapore</option>
                        <option value="BR">🇧🇷 Brazil</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="query"><i class="fas fa-search"></i> Product Search</label>
                    <input type="text" id="query" name="query" placeholder="e.g., iPhone 16 Pro, 128GB or boAt Airdopes 311 Pro" required>
                </div>
                <button type="submit" id="searchBtn">
                    <i class="fas fa-rocket"></i> Search Products
                </button>
            </form>
            
            <div id="results" class="results"></div>
        </div>
        
        <script>
            document.getElementById('searchForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const country = document.getElementById('country').value;
                const query = document.getElementById('query').value;
                const resultsDiv = document.getElementById('results');
                const searchBtn = document.getElementById('searchBtn');
                
                searchBtn.disabled = true;
                searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Searching...';
                
                resultsDiv.innerHTML = `
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Searching across multiple websites...</p>
                        <small>This may take 30-60 seconds for comprehensive results</small>
                    </div>
                `;
                
                try {
                    const response = await fetch('/api/search', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ country, query })
                    });
                    
                    const data = await response.json();
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<div class="error"><i class="fas fa-exclamation-triangle"></i> ${data.error}</div>`;
                    } else if (data.results && data.results.length > 0) {
                        let html = `
                            <div class="stats">
                                <h3><i class="fas fa-chart-bar"></i> Search Results</h3>
                                <p>Found <strong>${data.results.length}</strong> relevant products for "<strong>${query}</strong>" in <strong>${getCountryName(country)}</strong></p>
                            </div>
                        `;
                        
                        data.results.forEach((product, index) => {
                            const relevanceScore = Math.round((product.relevance_score || 0) * 100);
                            html += `
                                <div class="product">
                                    <div class="relevance-score">${relevanceScore}% match</div>
                                    <div class="product-header">
                                        <div>
                                            <div class="product-title">${product.productName}</div>
                                            <div class="price">
                                                ${product.currency}${product.price}
                                                ${product.original_price ? `<span class="original-price">${product.currency}${product.original_price}</span>` : ''}
                                                ${product.discount ? `<span class="discount">${product.discount} OFF</span>` : ''}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="product-info">
                                        <div class="info-item">
                                            <i class="fas fa-store"></i>
                                            <span><strong>Website:</strong> ${product.website}</span>
                                        </div>
                                        <div class="info-item">
                                            <i class="fas fa-box"></i>
                                            <span><strong>Availability:</strong> ${product.availability}</span>
                                        </div>
                                        ${product.rating ? `
                                            <div class="info-item">
                                                <i class="fas fa-star"></i>
                                                <span><strong>Rating:</strong> ${product.rating}</span>
                                            </div>
                                        ` : ''}
                                        ${product.reviews ? `
                                            <div class="info-item">
                                                <i class="fas fa-comments"></i>
                                                <span><strong>Reviews:</strong> ${product.reviews}</span>
                                            </div>
                                        ` : ''}
                                        <div class="info-item">
                                            <i class="fas fa-external-link-alt"></i>
                                            <a href="${product.link}" target="_blank" style="color: #667eea; text-decoration: none;">View Product</a>
                                        </div>
                                    </div>
                                </div>
                            `;
                        });
                        resultsDiv.innerHTML = html;
                    } else {
                        resultsDiv.innerHTML = `
                            <div class="no-results">
                                <i class="fas fa-search" style="font-size: 3em; color: #ccc; margin-bottom: 20px;"></i>
                                <h3>No products found</h3>
                                <p>Try a different search query or check the spelling</p>
                                <small>Examples: "iPhone 16 Pro", "Samsung Galaxy S24", "MacBook Air M2"</small>
                            </div>
                        `;
                    }
                } catch (error) {
                    resultsDiv.innerHTML = `
                        <div class="error">
                            <i class="fas fa-exclamation-triangle"></i> 
                            Error searching for products. Please try again.
                        </div>
                    `;
                    console.error('Search error:', error);
                } finally {
                    searchBtn.disabled = false;
                    searchBtn.innerHTML = '<i class="fas fa-rocket"></i> Search Products';
                }
            });
            
            function getCountryName(code) {
                const countries = {
                    'US': 'United States', 'IN': 'India', 'UK': 'United Kingdom',
                    'CA': 'Canada', 'AU': 'Australia', 'DE': 'Germany',
                    'FR': 'France', 'JP': 'Japan', 'SG': 'Singapore', 'BR': 'Brazil'
                };
                return countries[code] || code;
            }
        </script>
    </body>
    </html>
    """)

@app.route('/api/search', methods=['POST'])
def search_products():
    """API endpoint for product search"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        country = data.get('country', 'US')
        query = data.get('query', '')
        
        if not query or len(query.strip()) < 2:
            return jsonify({'error': 'Query must be at least 2 characters long'}), 400
        
        valid_countries = ['US', 'IN', 'UK', 'CA', 'AU', 'DE', 'FR', 'JP', 'SG', 'BR']
        if country.upper() not in valid_countries:
            return jsonify({'error': f'Country must be one of: {", ".join(valid_countries)}'}), 400
        
        results = price_tool.compare_prices(country.upper(), query.strip())
        
        return jsonify({
            'results': results,
            'total_count': len(results),
            'country': country.upper(),
            'query': query.strip(),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Search API error: {e}")
        return jsonify({'error': 'Internal server error. Please try again later.'}), 500

@app.route('/api/countries', methods=['GET'])
def get_supported_countries():
    """Get list of supported countries"""
    countries = [
        {'code': 'US', 'name': 'United States', 'currency': '$'},
        {'code': 'IN', 'name': 'India', 'currency': '₹'},
        {'code': 'UK', 'name': 'United Kingdom', 'currency': '£'},
        {'code': 'CA', 'name': 'Canada', 'currency': 'C$'},
        {'code': 'AU', 'name': 'Australia', 'currency': 'A$'},
        {'code': 'DE', 'name': 'Germany', 'currency': '€'},
        {'code': 'FR', 'name': 'France', 'currency': '€'},
        {'code': 'JP', 'name': 'Japan', 'currency': '¥'},
        {'code': 'SG', 'name': 'Singapore', 'currency': 'S$'},
        {'code': 'BR', 'name': 'Brazil', 'currency': 'R$'}
    ]
    return jsonify({'countries': countries})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        cache = CacheManager()
        cache.set('health_test', {'status': 'ok'})
        test_data = cache.get('health_test')
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'cache': 'working' if test_data else 'error',
            'version': '2.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting Universal Price Comparison Tool...")
    logger.info("Enhanced version with Windows compatibility")
    
    Path('logs').mkdir(exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)