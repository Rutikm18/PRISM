import asyncio
import httpx
import time
import hashlib
import random
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import quote_plus, urljoin, urlparse
import logging

# Import configuration - CRITICAL: This must be imported correctly
try:
    from config_global_price import MARKETPLACE_CONFIGS, RATE_LIMITS, USER_AGENTS
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("❌ Make sure config_global_price.py exists and is in the same directory")
    exit(1)

logger = logging.getLogger(__name__)

@dataclass
class PriceResult:
    """Standardized price result structure"""
    title: str
    price: float
    currency: str
    source: str
    url: str
    availability: str = "Available"
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    image_url: Optional[str] = None
    seller: Optional[str] = None
    shipping_cost: Optional[float] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class RateLimiter:
    """High-performance async rate limiter"""
    
    def __init__(self, requests_per_second: float, burst: int = 1):
        self.rate = requests_per_second
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                sleep_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(sleep_time)
                self.tokens = 0
                return True

class BaseScraper:
    """Base class for all marketplace scrapers"""
    
    def __init__(self, marketplace_name: str):
        self.marketplace_name = marketplace_name
        self.rate_limiter = RateLimiter(
            RATE_LIMITS.get(marketplace_name.lower(), RATE_LIMITS['default'])['requests_per_second'],
            RATE_LIMITS.get(marketplace_name.lower(), RATE_LIMITS['default'])['burst']
        )
    
    def get_headers(self) -> Dict[str, str]:
        """Get random headers to avoid detection"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
        
        # Remove currency symbols and extra characters
        price_clean = re.sub(r'[^\d.,]', '', price_text.replace(',', ''))
        
        # Handle different decimal separators
        if '.' in price_clean:
            try:
                return float(price_clean)
            except ValueError:
                return None
        
        try:
            return float(price_clean)
        except ValueError:
            return None

class AmazonScraper(BaseScraper):
    """Amazon web scraper for all countries"""
    
    def __init__(self):
        super().__init__('amazon')
    
    async def search_products(self, query: str, country: str, client: httpx.AsyncClient) -> List[PriceResult]:
        """Search Amazon products via scraping"""
        await self.rate_limiter.acquire()
        
        config = MARKETPLACE_CONFIGS.get(country, {}).get('amazon', {})
        if not config:
            return []
        
        search_url = f"https://{config['domain']}/s?k={quote_plus(query)}&ref=sr_pg_1"
        
        try:
            response = await client.get(search_url, headers=self.get_headers(), timeout=15.0)
            if response.status_code != 200:
                return []
            
            return self._parse_amazon_html(response.text, config)
        
        except Exception as e:
            logger.error(f"Amazon scraping error: {e}")
            return []
    
    def _parse_amazon_html(self, html: str, config: Dict) -> List[PriceResult]:
        """Parse Amazon HTML response"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Multiple selectors for different Amazon layouts
        selectors = [
            '[data-component-type="s-search-result"]',
            '.s-result-item[data-asin]',
            '.sg-col-inner .s-widget-container'
        ]
        
        products = []
        for selector in selectors:
            products = soup.select(selector)
            if products:
                break
        
        for container in products[:8]:
            try:
                # Try multiple title selectors
                title = None
                title_selectors = [
                    'h2 a span',
                    'h2 .a-link-normal',
                    '.s-link-style a h2',
                    '[data-cy="title-recipe-link"]'
                ]
                
                for sel in title_selectors:
                    title_elem = container.select_one(sel)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                if not title:
                    continue
                
                # Try multiple price selectors
                price = None
                price_selectors = [
                    '.a-price-whole',
                    '.a-price .a-offscreen',
                    '.a-price-symbol + .a-price-whole',
                    '.a-price-range .a-price .a-offscreen'
                ]
                
                for sel in price_selectors:
                    price_elem = container.select_one(sel)
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        price = self.extract_price(price_text)
                        if price:
                            break
                
                if not price:
                    continue
                
                # Get product URL
                link_elem = container.select_one('h2 a, .s-link-style a')
                if not link_elem or not link_elem.get('href'):
                    continue
                
                url = urljoin(f"https://{config['domain']}", link_elem['href'])
                
                # Extract rating
                rating = None
                rating_elem = container.select_one('.a-icon-alt')
                if rating_elem:
                    rating_text = rating_elem.get_text()
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                
                # Extract image
                image_url = None
                img_elem = container.select_one('img.s-image')
                if img_elem:
                    image_url = img_elem.get('src')
                
                result = PriceResult(
                    title=title[:100],  # Limit title length
                    price=price,
                    currency=config['currency'],
                    source="Amazon",
                    url=url,
                    availability="Available",
                    rating=rating,
                    image_url=image_url
                )
                results.append(result)
            
            except Exception as e:
                logger.debug(f"Error parsing Amazon product: {e}")
                continue
        
        return results

class EbayScraper(BaseScraper):
    """eBay web scraper"""
    
    def __init__(self):
        super().__init__('ebay')
    
    async def search_products(self, query: str, country: str, client: httpx.AsyncClient) -> List[PriceResult]:
        """Search eBay products via scraping"""
        await self.rate_limiter.acquire()
        
        config = MARKETPLACE_CONFIGS.get(country, {}).get('ebay', {})
        if not config:
            return []
        
        search_url = f"https://{config['domain']}/sch/i.html?_nkw={quote_plus(query)}&_sacat=0&LH_BIN=1&_sop=15"
        
        try:
            response = await client.get(search_url, headers=self.get_headers(), timeout=15.0)
            if response.status_code != 200:
                return []
            
            return self._parse_ebay_html(response.text, config)
        
        except Exception as e:
            logger.error(f"eBay scraping error: {e}")
            return []
    
    def _parse_ebay_html(self, html: str, config: Dict) -> List[PriceResult]:
        """Parse eBay HTML response"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # eBay search result containers
        products = soup.select('.s-item')
        
        for container in products[:6]:
            try:
                # Skip ads
                if container.select_one('.s-item__wrapper[data-viewport]'):
                    continue
                
                title_elem = container.select_one('.s-item__title')
                price_elem = container.select_one('.s-item__price .notranslate')
                link_elem = container.select_one('.s-item__link')
                
                if not all([title_elem, price_elem, link_elem]):
                    continue
                
                title = title_elem.get_text(strip=True)
                if title.lower().startswith('shop on ebay'):
                    continue
                
                price_text = price_elem.get_text(strip=True)
                price = self.extract_price(price_text)
                
                if not price:
                    continue
                
                url = link_elem['href']
                
                # Extract shipping cost
                shipping_elem = container.select_one('.s-item__shipping')
                shipping_cost = None
                if shipping_elem:
                    shipping_text = shipping_elem.get_text(strip=True)
                    if 'free' not in shipping_text.lower():
                        shipping_cost = self.extract_price(shipping_text)
                
                # Extract condition/availability
                condition_elem = container.select_one('.s-item__subtitle')
                availability = "Available"
                if condition_elem:
                    condition_text = condition_elem.get_text(strip=True)
                    if 'sold' in condition_text.lower():
                        availability = "Sold"
                
                result = PriceResult(
                    title=title[:100],
                    price=price,
                    currency=config['currency'],
                    source="eBay",
                    url=url,
                    availability=availability,
                    shipping_cost=shipping_cost
                )
                results.append(result)
            
            except Exception as e:
                logger.debug(f"Error parsing eBay product: {e}")
                continue
        
        return results

class WalmartScraper(BaseScraper):
    """Walmart web scraper"""
    
    def __init__(self):
        super().__init__('walmart')
    
    async def search_products(self, query: str, country: str, client: httpx.AsyncClient) -> List[PriceResult]:
        """Search Walmart products via scraping"""
        await self.rate_limiter.acquire()
        
        config = MARKETPLACE_CONFIGS.get(country, {}).get('walmart', {})
        if not config:
            return []
        
        search_url = f"https://{config['domain']}/search?q={quote_plus(query)}"
        
        try:
            response = await client.get(search_url, headers=self.get_headers(), timeout=15.0)
            if response.status_code != 200:
                return []
            
            return self._parse_walmart_html(response.text, config)
        
        except Exception as e:
            logger.error(f"Walmart scraping error: {e}")
            return []
    
    def _parse_walmart_html(self, html: str, config: Dict) -> List[PriceResult]:
        """Parse Walmart HTML response"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Walmart product containers
        selectors = [
            '[data-testid="item-stack"]',
            '[data-automation-id="product-tile"]',
            '.mb1.ph1.pa0-xl.bb.b--near-white.w-25'
        ]
        
        products = []
        for selector in selectors:
            products = soup.select(selector)
            if products:
                break
        
        for container in products[:6]:
            try:
                title_elem = container.select_one('[data-automation-id="product-title"], [data-testid="product-title"]')
                price_elem = container.select_one('[data-automation-id="product-price"] .w_iUH7, .f2.b.lh-copy.dark-gray')
                link_elem = container.select_one('a[href*="/ip/"]')
                
                if not all([title_elem, price_elem, link_elem]):
                    continue
                
                title = title_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                price = self.extract_price(price_text)
                
                if not price:
                    continue
                
                url = urljoin(f"https://{config['domain']}", link_elem['href'])
                
                result = PriceResult(
                    title=title[:100],
                    price=price,
                    currency=config['currency'],
                    source="Walmart",
                    url=url,
                    availability="Available"
                )
                results.append(result)
            
            except Exception as e:
                logger.debug(f"Error parsing Walmart product: {e}")
                continue
        
        return results

class FlipkartScraper(BaseScraper):
    """Flipkart web scraper for India"""
    
    def __init__(self):
        super().__init__('flipkart')
    
    async def search_products(self, query: str, country: str, client: httpx.AsyncClient) -> List[PriceResult]:
        """Search Flipkart products via scraping"""
        await self.rate_limiter.acquire()
        
        config = MARKETPLACE_CONFIGS.get(country, {}).get('flipkart', {})
        if not config:
            return []
        
        search_url = f"https://{config['domain']}/search?q={quote_plus(query)}&sort=price_asc"
        
        try:
            response = await client.get(search_url, headers=self.get_headers(), timeout=15.0)
            if response.status_code != 200:
                return []
            
            return self._parse_flipkart_html(response.text, config)
        
        except Exception as e:
            logger.error(f"Flipkart scraping error: {e}")
            return []
    
    def _parse_flipkart_html(self, html: str, config: Dict) -> List[PriceResult]:
        """Parse Flipkart HTML response"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Flipkart product containers
        products = soup.select('[data-id]')
        
        for container in products[:6]:
            try:
                title_elem = container.select_one('a[title], .IRpwTa')
                price_elem = container.select_one('._30jeq3, ._1_WHN1')
                link_elem = container.select_one('a[href*="/p/"]')
                
                if not all([title_elem, price_elem, link_elem]):
                    continue
                
                title = title_elem.get('title') or title_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                price = self.extract_price(price_text)
                
                if not price:
                    continue
                
                url = urljoin(f"https://{config['domain']}", link_elem['href'])
                
                # Extract rating
                rating = None
                rating_elem = container.select_one('._3LWZlK')
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                
                result = PriceResult(
                    title=title[:100],
                    price=price,
                    currency=config['currency'],
                    source="Flipkart",
                    url=url,
                    availability="Available",
                    rating=rating
                )
                results.append(result)
            
            except Exception as e:
                logger.debug(f"Error parsing Flipkart product: {e}")
                continue
        
        return results

class TargetScraper(BaseScraper):
    """Target web scraper"""
    
    def __init__(self):
        super().__init__('target')
    
    async def search_products(self, query: str, country: str, client: httpx.AsyncClient) -> List[PriceResult]:
        """Search Target products via scraping"""
        await self.rate_limiter.acquire()
        
        config = MARKETPLACE_CONFIGS.get(country, {}).get('target', {})
        if not config:
            return []
        
        search_url = f"https://{config['domain']}/s?searchTerm={quote_plus(query)}"
        
        try:
            response = await client.get(search_url, headers=self.get_headers(), timeout=15.0)
            if response.status_code != 200:
                return []
            
            return self._parse_target_html(response.text, config)
        
        except Exception as e:
            logger.error(f"Target scraping error: {e}")
            return []
    
    def _parse_target_html(self, html: str, config: Dict) -> List[PriceResult]:
        """Parse Target HTML response"""
        results = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Target product containers
        products = soup.select('[data-test="product-details"]')
        
        for container in products[:6]:
            try:
                title_elem = container.select_one('[data-test="product-title"]')
                price_elem = container.select_one('[data-test="product-price"]')
                link_elem = container.select_one('a[href*="/p/"]')
                
                if not all([title_elem, price_elem, link_elem]):
                    continue
                
                title = title_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                price = self.extract_price(price_text)
                
                if not price:
                    continue
                
                url = urljoin(f"https://{config['domain']}", link_elem['href'])
                
                result = PriceResult(
                    title=title[:100],
                    price=price,
                    currency=config['currency'],
                    source="Target",
                    url=url,
                    availability="Available"
                )
                results.append(result)
            
            except Exception as e:
                logger.debug(f"Error parsing Target product: {e}")
                continue
        
        return results