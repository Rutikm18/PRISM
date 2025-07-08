import os
from typing import Dict, List



# Global marketplace URLs and configurations for scraping
MARKETPLACE_CONFIGS = {
    'US': {
        'ebay': {'domain': 'ebay.com', 'currency': 'USD'},
        'walmart': {'domain': 'walmart.com', 'currency': 'USD'},
        'amazon': {'domain': 'amazon.com', 'currency': 'USD'},
        'target': {'domain': 'target.com', 'currency': 'USD'},
        'newegg': {'domain': 'newegg.com', 'currency': 'USD'},
        'etsy': {'domain': 'etsy.com', 'currency': 'USD'}
    },
    'CA': {
        'ebay': {'domain': 'ebay.ca', 'currency': 'CAD'},
        'walmart': {'domain': 'walmart.ca', 'currency': 'CAD'},
        'amazon': {'domain': 'amazon.ca', 'currency': 'CAD'},
        'newegg': {'domain': 'newegg.ca', 'currency': 'CAD'},
        'bestbuy': {'domain': 'bestbuy.ca', 'currency': 'CAD'}
    },
    'UK': {
        'ebay': {'domain': 'ebay.co.uk', 'currency': 'GBP'},
        'amazon': {'domain': 'amazon.co.uk', 'currency': 'GBP'},
        'argos': {'domain': 'argos.co.uk', 'currency': 'GBP'},
        'tesco': {'domain': 'tesco.com', 'currency': 'GBP'}
    },
    'DE': {
        'ebay': {'domain': 'ebay.de', 'currency': 'EUR'},
        'amazon': {'domain': 'amazon.de', 'currency': 'EUR'},
        'otto': {'domain': 'otto.de', 'currency': 'EUR'},
        'mediamarkt': {'domain': 'mediamarkt.de', 'currency': 'EUR'}
    },
    'FR': {
        'ebay': {'domain': 'ebay.fr', 'currency': 'EUR'},
        'amazon': {'domain': 'amazon.fr', 'currency': 'EUR'},
        'fnac': {'domain': 'fnac.com', 'currency': 'EUR'},
        'cdiscount': {'domain': 'cdiscount.com', 'currency': 'EUR'}
    },
    'IN': {
        'amazon': {'domain': 'amazon.in', 'currency': 'INR'},
        'flipkart': {'domain': 'flipkart.com', 'currency': 'INR'},
        'snapdeal': {'domain': 'snapdeal.com', 'currency': 'INR'},
        'myntra': {'domain': 'myntra.com', 'currency': 'INR'},
        'ajio': {'domain': 'ajio.com', 'currency': 'INR'}
    },
    'JP': {
        'amazon': {'domain': 'amazon.co.jp', 'currency': 'JPY'},
        'rakuten': {'domain': 'rakuten.co.jp', 'currency': 'JPY'},
        'yahoo': {'domain': 'shopping.yahoo.co.jp', 'currency': 'JPY'},
        'mercari': {'domain': 'mercari.com', 'currency': 'JPY'}
    },
    'AU': {
        'amazon': {'domain': 'amazon.com.au', 'currency': 'AUD'},
        'ebay': {'domain': 'ebay.com.au', 'currency': 'AUD'},
        'jbhifi': {'domain': 'jbhifi.com.au', 'currency': 'AUD'},
        'kmart': {'domain': 'kmart.com.au', 'currency': 'AUD'}
    },
    'BR': {
        'amazon': {'domain': 'amazon.com.br', 'currency': 'BRL'},
        'mercadolibre': {'domain': 'mercadolibre.com.br', 'currency': 'BRL'},
        'magazineluiza': {'domain': 'magazineluiza.com.br', 'currency': 'BRL'},
        'casasbahia': {'domain': 'casasbahia.com.br', 'currency': 'BRL'}
    },
    'SG': {
        'amazon': {'domain': 'amazon.sg', 'currency': 'SGD'},
        'lazada': {'domain': 'lazada.sg', 'currency': 'SGD'},
        'shopee': {'domain': 'shopee.sg', 'currency': 'SGD'},
        'qoo10': {'domain': 'qoo10.sg', 'currency': 'SGD'}
    }
}

# Rate limiting configurations for scraping (be respectful)
RATE_LIMITS = {
    'ebay': {'requests_per_second': 1, 'burst': 3},
    'amazon': {'requests_per_second': 0.5, 'burst': 2},
    'walmart': {'requests_per_second': 1, 'burst': 3},
    'target': {'requests_per_second': 1, 'burst': 3},
    'flipkart': {'requests_per_second': 1, 'burst': 3},
    'default': {'requests_per_second': 1, 'burst': 2}
}

# Cache configuration
CACHE_CONFIG = {
    'default_ttl': 1800,  # 30 minutes for scraping
    'max_size': 5000,
    'cleanup_interval': 3600  # 1 hour
}

# User agents for rotation to avoid detection
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]