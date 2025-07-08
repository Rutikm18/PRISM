# app.py
import asyncio
import json
import time
import sys
import traceback
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import logging

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("🚀 Starting Free Price Comparison System...")
print("=" * 60)

# Test imports step by step with detailed error handling
try:
    print("1️⃣ Importing configuration...")
    from config_global_price import MARKETPLACE_CONFIGS, RATE_LIMITS, CACHE_CONFIG, USER_AGENTS
    print(f"   ✅ Config loaded - {len(MARKETPLACE_CONFIGS)} countries supported")
except ImportError as e:
    print(f"   ❌ Config import failed: {e}")
    print("   💡 Make sure config_global_price.py exists in the same directory")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Config error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("2️⃣ Importing marketplace scrapers...")
    from marketplace_apis import (
        AmazonScraper, EbayScraper, WalmartScraper, FlipkartScraper, TargetScraper,
        PriceResult
    )
    print("   ✅ All scrapers imported successfully")
except ImportError as e:
    print(f"   ❌ Scrapers import failed: {e}")
    print("   💡 Make sure marketplace_apis.py exists and is valid")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Scrapers error: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3️⃣ Importing price aggregator...")
    from global_price_aggregator import GlobalPriceAggregator
    print("   ✅ Aggregator imported successfully")
except ImportError as e:
    print(f"   ❌ Aggregator import failed: {e}")
    print("   💡 Make sure global_price_aggregator.py exists and is valid")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Aggregator error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize the global aggregator with error handling
try:
    print("4️⃣ Initializing price aggregator...")
    aggregator = GlobalPriceAggregator()
    print("   ✅ Aggregator initialized successfully")
    print(f"   📊 Cache stats: {aggregator.get_cache_stats()}")
except Exception as e:
    print(f"   ❌ Aggregator initialization failed: {e}")
    traceback.print_exc()
    sys.exit(1)

@app.route('/')
def index():
    """High-performance web interface"""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔥 Free Price Comparison System</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px;
            }
            .container { 
                max-width: 1200px; margin: 0 auto; background: rgba(255,255,255,0.95);
                padding: 40px; border-radius: 20px; backdrop-filter: blur(10px);
                box-shadow: 0 25px 50px rgba(0,0,0,0.15);
            }
            h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 2.8em; font-weight: 700; }
            .subtitle { text-align: center; color: #666; margin-bottom: 40px; font-size: 1.2em; }
            .free-badge { background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.9em; font-weight: 600; display: inline-block; margin-bottom: 20px; }
            .search-form { display: grid; grid-template-columns: 1fr 200px auto; gap: 15px; margin-bottom: 40px; }
            input, select { padding: 15px 20px; border: 2px solid #e0e0e0; border-radius: 12px; font-size: 16px; transition: all 0.3s ease; }
            input:focus, select:focus { border-color: #667eea; outline: none; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
            button { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 15px 30px; border: none; border-radius: 12px;
                font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s ease;
            }
            button:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
            button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
            .multi-country { margin: 20px 0; }
            .country-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 15px 0; }
            .country-checkbox { display: flex; align-items: center; gap: 8px; }
            .results { margin-top: 40px; }
            .country-section { margin-bottom: 40px; }
            .country-title { font-size: 1.5em; font-weight: 600; color: #333; margin-bottom: 20px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
            .product-card { 
                background: white; border-radius: 15px; padding: 25px; 
                box-shadow: 0 8px 25px rgba(0,0,0,0.1); transition: all 0.3s ease;
                border-left: 4px solid #667eea; position: relative; overflow: hidden;
            }
            .product-card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.15); }
            .product-title { font-size: 1.1em; font-weight: 600; color: #333; margin-bottom: 12px; line-height: 1.4; }
            .product-price { font-size: 1.8em; font-weight: 700; color: #28a745; margin-bottom: 15px; }
            .product-source { background: #f8f9fa; padding: 8px 12px; border-radius: 20px; font-size: 0.9em; color: #666; display: inline-block; }
            .product-meta { margin-top: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9em; color: #666; }
            .product-link { color: #667eea; text-decoration: none; font-weight: 600; margin-top: 10px; display: inline-block; }
            .product-link:hover { text-decoration: underline; }
            .loading { text-align: center; padding: 60px; }
            .spinner { width: 50px; height: 50px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; margin: 20px 0; }
            .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 10px; margin: 20px 0; }
            .performance-stats { background: #e7f3ff; padding: 15px; border-radius: 10px; margin: 20px 0; text-align: center; }
            .info-section { background: #f8f9fa; padding: 20px; border-radius: 12px; margin: 20px 0; }
            .info-title { font-weight: 600; color: #333; margin-bottom: 10px; }
            .marketplaces { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
            .marketplace-badge { background: #667eea; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; }
            @media (max-width: 768px) { 
                .search-form { grid-template-columns: 1fr; }
                .country-grid { grid-template-columns: repeat(2, 1fr); }
                .product-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 Free Price Comparison System</h1>
            <div class="free-badge">✨ 100% Free • No API Keys Required • Pure Web Scraping</div>
            <p class="subtitle">Lightning-fast global price comparison across major marketplaces</p>
            
            <div class="info-section">
                <div class="info-title">🌟 Supported Marketplaces by Country:</div>
                <div id="marketplace-info">Loading marketplace information...</div>
            </div>
            
            <div class="search-form">
                <input type="text" id="query" placeholder="Enter product name (e.g., iPhone 15 Pro, MacBook Air M2)" required>
                <select id="searchType">
                    <option value="single">Single Country</option>
                    <option value="multi">Multiple Countries</option>
                </select>
                <button onclick="searchProducts()" id="searchBtn">🔍 Search</button>
            </div>
            
            <div id="singleCountry">
                <select id="country">
                    <option value="US">🇺🇸 United States</option>
                    <option value="CA">🇨🇦 Canada</option>
                    <option value="UK">🇬🇧 United Kingdom</option>
                    <option value="DE">🇩🇪 Germany</option>
                    <option value="FR">🇫🇷 France</option>
                    <option value="IN">🇮🇳 India</option>
                    <option value="JP">🇯🇵 Japan</option>
                    <option value="AU">🇦🇺 Australia</option>
                    <option value="BR">🇧🇷 Brazil</option>
                    <option value="SG">🇸🇬 Singapore</option>
                </select>
            </div>
            
            <div id="multiCountry" class="multi-country" style="display: none;">
                <h3>Select Countries:</h3>
                <div class="country-grid">
                    <label class="country-checkbox"><input type="checkbox" value="US" checked> 🇺🇸 US</label>
                    <label class="country-checkbox"><input type="checkbox" value="CA"> 🇨🇦 Canada</label>
                    <label class="country-checkbox"><input type="checkbox" value="UK"> 🇬🇧 UK</label>
                    <label class="country-checkbox"><input type="checkbox" value="DE"> 🇩🇪 Germany</label>
                    <label class="country-checkbox"><input type="checkbox" value="FR"> 🇫🇷 France</label>
                    <label class="country-checkbox"><input type="checkbox" value="IN"> 🇮🇳 India</label>
                    <label class="country-checkbox"><input type="checkbox" value="JP"> 🇯🇵 Japan</label>
                    <label class="country-checkbox"><input type="checkbox" value="AU"> 🇦🇺 Australia</label>
                    <label class="country-checkbox"><input type="checkbox" value="BR"> 🇧🇷 Brazil</label>
                    <label class="country-checkbox"><input type="checkbox" value="SG"> 🇸🇬 Singapore</label>
                </div>
            </div>
            
            <div id="results" class="results"></div>
        </div>
        
        <script>
            // Load marketplace information on page load
            window.addEventListener('load', loadMarketplaceInfo);
            
            async function loadMarketplaceInfo() {
                try {
                    const response = await fetch('/api/countries');
                    const data = await response.json();
                    
                    let html = '';
                    for (const [country, info] of Object.entries(data)) {
                        const countryNames = {
                            'US': '🇺🇸 US', 'CA': '🇨🇦 Canada', 'UK': '🇬🇧 UK',
                            'DE': '🇩🇪 Germany', 'FR': '🇫🇷 France', 'IN': '🇮🇳 India',
                            'JP': '🇯🇵 Japan', 'AU': '🇦🇺 Australia', 'BR': '🇧🇷 Brazil', 'SG': '🇸🇬 Singapore'
                        };
                        
                        html += `<div style="margin-bottom: 10px;"><strong>${countryNames[country]}:</strong> `;
                        html += '<div class="marketplaces">';
                        info.marketplaces.forEach(marketplace => {
                            html += `<span class="marketplace-badge">${marketplace}</span>`;
                        });
                        html += '</div></div>';
                    }
                    
                    document.getElementById('marketplace-info').innerHTML = html;
                } catch (error) {
                    console.error('Error loading marketplace info:', error);
                    document.getElementById('marketplace-info').innerHTML = 'Unable to load marketplace information.';
                }
            }
            
            document.getElementById('searchType').addEventListener('change', function() {
                const single = document.getElementById('singleCountry');
                const multi = document.getElementById('multiCountry');
                if (this.value === 'multi') {
                    single.style.display = 'none';
                    multi.style.display = 'block';
                } else {
                    single.style.display = 'block';
                    multi.style.display = 'none';
                }
            });
            
            async function searchProducts() {
                const query = document.getElementById('query').value.trim();
                const searchType = document.getElementById('searchType').value;
                const resultsDiv = document.getElementById('results');
                const searchBtn = document.getElementById('searchBtn');
                
                if (!query) {
                    alert('Please enter a product name');
                    return;
                }
                
                if (query.length < 2) {
                    alert('Please enter at least 2 characters');
                    return;
                }
                
                const startTime = performance.now();
                searchBtn.disabled = true;
                searchBtn.textContent = '🔄 Searching...';
                resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>🚀 Scraping multiple marketplaces... This may take 15-30 seconds.</p></div>';
                
                try {
                    let response;
                    
                    if (searchType === 'single') {
                        const country = document.getElementById('country').value;
                        response = await fetch('/api/search', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query, country })
                        });
                    } else {
                        const countries = Array.from(document.querySelectorAll('#multiCountry input:checked')).map(cb => cb.value);
                        if (countries.length === 0) {
                            alert('Please select at least one country');
                            return;
                        }
                        if (countries.length > 5) {
                            alert('Maximum 5 countries allowed for better performance');
                            return;
                        }
                        response = await fetch('/api/search-multi', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query, countries })
                        });
                    }
                    
                    const data = await response.json();
                    const endTime = performance.now();
                    const duration = ((endTime - startTime) / 1000).toFixed(2);
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<div class="error">❌ ${data.error}</div>`;
                        return;
                    }
                    
                    displayResults(data, duration, searchType);
                    
                } catch (error) {
                    resultsDiv.innerHTML = '<div class="error">❌ Network error. Please try again. Make sure you have a stable internet connection.</div>';
                    console.error('Search error:', error);
                } finally {
                    searchBtn.disabled = false;
                    searchBtn.textContent = '🔍 Search';
                }
            }
            
            function displayResults(data, duration, searchType) {
                const resultsDiv = document.getElementById('results');
                let html = `<div class="success">✅ Search completed in ${duration}s - Results found via web scraping!</div>`;
                
                if (searchType === 'single') {
                    html += displaySingleCountryResults(data.results);
                } else {
                    html += displayMultiCountryResults(data.results);
                }
                
                resultsDiv.innerHTML = html;
            }
            
            function displaySingleCountryResults(results) {
                if (!results || results.length === 0) {
                    return '<div class="error">No products found. Try different keywords or check your spelling.</div>';
                }
                
                let html = '<div class="product-grid">';
                results.forEach(product => {
                    html += `
                        <div class="product-card">
                            <div class="product-title">${escapeHtml(product.title)}</div>
                            <div class="product-price">${product.currency} ${product.price.toFixed(2)}</div>
                            <div class="product-source">📍 ${product.source}</div>
                            <div class="product-meta">
                                <div><strong>Status:</strong> ${product.availability}</div>
                                <div><strong>Rating:</strong> ${product.rating ? product.rating.toFixed(1) + '/5' : 'N/A'}</div>
                            </div>
                            ${product.shipping_cost ? `<div style="margin-top: 8px; font-size: 0.9em; color: #666;">🚚 Shipping: ${product.currency} ${product.shipping_cost.toFixed(2)}</div>` : ''}
                            <a href="${product.url}" target="_blank" class="product-link">View Product →</a>
                        </div>
                    `;
                });
                html += '</div>';
                return html;
            }
            
            function displayMultiCountryResults(results) {
                let html = '';
                
                for (const [country, products] of Object.entries(results)) {
                    const countryNames = {
                        'US': '🇺🇸 United States', 'CA': '🇨🇦 Canada', 'UK': '🇬🇧 United Kingdom',
                        'DE': '🇩🇪 Germany', 'FR': '🇫🇷 France', 'IN': '🇮🇳 India',
                        'JP': '🇯🇵 Japan', 'AU': '🇦🇺 Australia', 'BR': '🇧🇷 Brazil', 'SG': '🇸🇬 Singapore'
                    };
                    
                    html += `<div class="country-section">`;
                    html += `<div class="country-title">${countryNames[country]} (${products.length} results)</div>`;
                    
                    if (products.length > 0) {
                        html += '<div class="product-grid">';
                        products.slice(0, 8).forEach(product => {
                            html += `
                                <div class="product-card">
                                    <div class="product-title">${escapeHtml(product.title)}</div>
                                    <div class="product-price">${product.currency} ${product.price.toFixed(2)}</div>
                                    <div class="product-source">📍 ${product.source}</div>
                                    <div class="product-meta">
                                        <div><strong>Status:</strong> ${product.availability}</div>
                                        <div><strong>Rating:</strong> ${product.rating ? product.rating.toFixed(1) + '/5' : 'N/A'}</div>
                                    </div>
                                    ${product.shipping_cost ? `<div style="margin-top: 8px; font-size: 0.9em; color: #666;">🚚 Shipping: ${product.currency} ${product.shipping_cost.toFixed(2)}</div>` : ''}
                                    <a href="${product.url}" target="_blank" class="product-link">View Product →</a>
                                </div>
                            `;
                        });
                        html += '</div>';
                    } else {
                        html += '<p style="color: #666; text-align: center; padding: 20px;">No products found in this country. Try different keywords.</p>';
                    }
                    
                    html += '</div>';
                }
                
                return html;
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Enable Enter key search
            document.getElementById('query').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchProducts();
                }
            });
        </script>
    </body>
    </html>
    """)

@app.route('/api/search', methods=['POST'])
async def search_single_country():
    """Search products in a single country"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        country = data.get('country', 'US').upper()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if len(query) < 2:
            return jsonify({'error': 'Query must be at least 2 characters'}), 400
        
        if len(query) > 100:
            return jsonify({'error': 'Query too long (max 100 characters)'}), 400
        
        logger.info(f"Searching for '{query}' in {country}")
        
        # Get prices using the aggregator
        results = await aggregator.get_all_prices(query, country)
        
        return jsonify({
            'results': results,
            'total_count': len(results),
            'country': country,
            'query': query,
            'timestamp': time.time(),
            'cache_stats': aggregator.get_cache_stats()
        })
        
    except Exception as e:
        logger.error(f"Single country search error: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/api/search-multi', methods=['POST'])
async def search_multiple_countries():
    """Search products in multiple countries"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        countries = data.get('countries', ['US'])
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if len(query) < 2:
            return jsonify({'error': 'Query must be at least 2 characters'}), 400
        
        if not countries:
            return jsonify({'error': 'At least one country is required'}), 400
        
        if len(countries) > 5:
            return jsonify({'error': 'Maximum 5 countries allowed for better performance'}), 400
        
        logger.info(f"Multi-country search for '{query}' in {countries}")
        
        # Get prices for multiple countries
        results = await aggregator.get_prices_multiple_countries(query, countries)
        
        return jsonify({
            'results': results,
            'countries': countries,
            'query': query,
            'timestamp': time.time(),
            'cache_stats': aggregator.get_cache_stats()
        })
        
    except Exception as e:
        logger.error(f"Multi-country search error: {e}")
        return jsonify({'error': f'Multi-country search failed: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cache_stats': aggregator.get_cache_stats(),
        'supported_countries': list(MARKETPLACE_CONFIGS.keys()),
        'version': '2.0.0-scraping',
        'scrapers': ['Amazon', 'eBay', 'Walmart', 'Flipkart', 'Target']
    })

@app.route('/api/countries')
def get_countries():
    """Get supported countries and their marketplaces"""
    try:
        country_info = {}
        for country, marketplaces in MARKETPLACE_CONFIGS.items():
            country_info[country] = {
                'marketplaces': list(marketplaces.keys()),
                'currency': list(marketplaces.values())[0].get('currency', 'USD')
            }
        
        return jsonify(country_info)
    except Exception as e:
        logger.error(f"Countries endpoint error: {e}")
        return jsonify({'error': 'Failed to get countries info'}), 500

@app.route('/api/test')
def test_endpoint():
    """Test endpoint to verify the API is working"""
    return jsonify({
        'status': 'working',
        'message': 'Price Comparison API is running successfully!',
        'timestamp': time.time(),
        'version': '2.0.0-scraping',
        'endpoints': ['/api/health', '/api/countries', '/api/search', '/api/search-multi']
    })

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the cache (admin endpoint)"""
    try:
        aggregator.clear_cache()
        logger.info("Cache cleared via API")
        return jsonify({'message': 'Cache cleared successfully'})
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({'error': 'Failed to clear cache'}), 500

# Command-line interface for testing
async def cli_search():
    """Command-line interface for testing"""
    print("🚀 Free Price Comparison System - CLI Mode")
    print("✨ No API Keys Required - Pure Web Scraping")
    print("=" * 60)
    
    while True:
        try:
            query = input("\nEnter product name (or 'quit' to exit): ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            if len(query) < 2:
                print("❌ Query must be at least 2 characters")
                continue
            
            country = input("Enter country code (US, CA, UK, DE, FR, IN, JP, AU, BR, SG): ").strip().upper()
            if not country:
                country = 'US'
            
            if country not in MARKETPLACE_CONFIGS:
                print(f"❌ Unsupported country: {country}")
                print(f"Supported countries: {', '.join(MARKETPLACE_CONFIGS.keys())}")
                continue
            
            print(f"\n🔍 Searching for '{query}' in {country}...")
            print("⏳ This may take 15-30 seconds (web scraping multiple sites)...")
            start_time = time.time()
            
            results = await aggregator.get_all_prices(query, country)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"⚡ Search completed in {duration:.2f}s")
            print(f"📊 Found {len(results)} products")
            print("-" * 80)
            
            if results:
                for i, product in enumerate(results[:10], 1):
                    print(f"{i:2d}. {product['source']:<12} | {product['currency']} {product['price']:>8.2f} | {product['title'][:50]}")
                    if product.get('rating'):
                        print(f"     ⭐ {product['rating']:.1f}/5")
                    if product.get('shipping_cost'):
                        print(f"     🚚 Shipping: {product['currency']} {product['shipping_cost']:.2f}")
                    print(f"     🔗 {product['url']}")
                    print()
                
                if len(results) > 10:
                    print(f"... and {len(results) - 10} more results")
            else:
                print("❌ No products found. Try different keywords.")
                print("💡 Tips:")
                print("   - Use simpler, more common product names")
                print("   - Try brand names (e.g., 'Apple iPhone' instead of 'smartphone')")
                print("   - Check your spelling")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"CLI search error: {e}")

def run_performance_test():
    """Run a performance test"""
    print("🧪 Running Performance Test...")
    print("=" * 40)
    
    async def test():
        test_queries = ["iPhone 15", "MacBook Air", "Samsung Galaxy S24"]
        test_countries = ["US", "CA", "UK"]
        
        for query in test_queries:
            for country in test_countries:
                print(f"\n🔍 Testing: '{query}' in {country}")
                start_time = time.time()
                
                try:
                    results = await aggregator.get_all_prices(query, country)
                    duration = time.time() - start_time
                    print(f"   ✅ {len(results)} results in {duration:.2f}s")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        # Test cache performance
        print(f"\n📊 Cache Stats: {aggregator.get_cache_stats()}")
    
    asyncio.run(test())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'cli':
            # Run CLI mode
            print("5️⃣ Starting CLI mode...")
            asyncio.run(cli_search())
        elif sys.argv[1] == 'test':
            # Run performance test
            print("5️⃣ Starting performance test...")
            run_performance_test()
        else:
            print("Usage:")
            print("  python app.py          # Run web server")
            print("  python app.py cli      # Run CLI mode")
            print("  python app.py test     # Run performance test")
    else:
        # Run web server
        print("5️⃣ Starting Flask web server...")
        print("🌐 Web interface: http://localhost:5000")
        print("🧪 Test endpoint: http://localhost:5000/api/test")
        print("🏥 Health check: http://localhost:5000/api/health")
        print("🗺️  Countries: http://localhost:5000/api/countries")
        print("⚠️  Press Ctrl+C to stop the server")
        print("-" * 60)
        print("💡 Tips for better results:")
        print("   - Use specific product names (e.g., 'iPhone 15 Pro' vs 'phone')")
        print("   - Include brand names when possible")
        print("   - Be patient - web scraping takes 15-30 seconds")
        print("   - Results are cached for 30 minutes")
        print("-" * 60)
        
        try:
            # Start the Flask development server
            app.run(
                debug=True, 
                host='127.0.0.1',  # Localhost only for security
                port=5000, 
                threaded=True,
                use_reloader=False  # Disable reloader to avoid import issues
            )
        except KeyboardInterrupt:
            print("\n👋 Server stopped. Goodbye!")
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            print("\n🔧 Troubleshooting:")
            print("1. Check if port 5000 is already in use")
            print("2. Try a different port: modify port=5000 to port=8080")
            print("3. Run as administrator/sudo if needed")
            print("4. Check your firewall settings")
            print("5. Ensure all dependencies are installed: pip install -r requirements.txt")
    # app.py
import asyncio
import json
import time
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import logging

# Import configuration
from config_global_price import MARKETPLACE_CONFIGS, RATE_LIMITS, CACHE_CONFIG, USER_AGENTS

# Import scrapers and aggregator
from marketplace_apis import (
    AmazonScraper, EbayScraper, WalmartScraper, FlipkartScraper, TargetScraper,
    PriceResult
)
from global_price_aggregator import GlobalPriceAggregator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize the global aggregator
aggregator = GlobalPriceAggregator()

@app.route('/')
def index():
    """High-performance web interface"""
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🔥 Free Price Comparison System</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; padding: 20px;
            }
            .container { 
                max-width: 1200px; margin: 0 auto; background: rgba(255,255,255,0.95);
                padding: 40px; border-radius: 20px; backdrop-filter: blur(10px);
                box-shadow: 0 25px 50px rgba(0,0,0,0.15);
            }
            h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 2.8em; font-weight: 700; }
            .subtitle { text-align: center; color: #666; margin-bottom: 40px; font-size: 1.2em; }
            .free-badge { background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 8px 16px; border-radius: 20px; font-size: 0.9em; font-weight: 600; display: inline-block; margin-bottom: 20px; }
            .search-form { display: grid; grid-template-columns: 1fr 200px auto; gap: 15px; margin-bottom: 40px; }
            input, select { padding: 15px 20px; border: 2px solid #e0e0e0; border-radius: 12px; font-size: 16px; transition: all 0.3s ease; }
            input:focus, select:focus { border-color: #667eea; outline: none; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
            button { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 15px 30px; border: none; border-radius: 12px;
                font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s ease;
            }
            button:hover { transform: translateY(-2px); box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4); }
            button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
            .multi-country { margin: 20px 0; }
            .country-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 15px 0; }
            .country-checkbox { display: flex; align-items: center; gap: 8px; }
            .results { margin-top: 40px; }
            .country-section { margin-bottom: 40px; }
            .country-title { font-size: 1.5em; font-weight: 600; color: #333; margin-bottom: 20px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
            .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
            .product-card { 
                background: white; border-radius: 15px; padding: 25px; 
                box-shadow: 0 8px 25px rgba(0,0,0,0.1); transition: all 0.3s ease;
                border-left: 4px solid #667eea; position: relative; overflow: hidden;
            }
            .product-card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.15); }
            .product-title { font-size: 1.1em; font-weight: 600; color: #333; margin-bottom: 12px; line-height: 1.4; }
            .product-price { font-size: 1.8em; font-weight: 700; color: #28a745; margin-bottom: 15px; }
            .product-source { background: #f8f9fa; padding: 8px 12px; border-radius: 20px; font-size: 0.9em; color: #666; display: inline-block; }
            .product-meta { margin-top: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9em; color: #666; }
            .product-link { color: #667eea; text-decoration: none; font-weight: 600; margin-top: 10px; display: inline-block; }
            .product-link:hover { text-decoration: underline; }
            .loading { text-align: center; padding: 60px; }
            .spinner { width: 50px; height: 50px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 10px; margin: 20px 0; }
            .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 10px; margin: 20px 0; }
            .performance-stats { background: #e7f3ff; padding: 15px; border-radius: 10px; margin: 20px 0; text-align: center; }
            .info-section { background: #f8f9fa; padding: 20px; border-radius: 12px; margin: 20px 0; }
            .info-title { font-weight: 600; color: #333; margin-bottom: 10px; }
            .marketplaces { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
            .marketplace-badge { background: #667eea; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; }
            @media (max-width: 768px) { 
                .search-form { grid-template-columns: 1fr; }
                .country-grid { grid-template-columns: repeat(2, 1fr); }
                .product-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 Free Price Comparison System</h1>
            <div class="free-badge">✨ 100% Free • No API Keys Required • Pure Web Scraping</div>
            <p class="subtitle">Lightning-fast global price comparison across major marketplaces</p>
            
            <div class="info-section">
                <div class="info-title">🌟 Supported Marketplaces by Country:</div>
                <div id="marketplace-info"></div>
            </div>
            
            <div class="search-form">
                <input type="text" id="query" placeholder="Enter product name (e.g., iPhone 15 Pro, MacBook Air M2)" required>
                <select id="searchType">
                    <option value="single">Single Country</option>
                    <option value="multi">Multiple Countries</option>
                </select>
                <button onclick="searchProducts()" id="searchBtn">🔍 Search</button>
            </div>
            
            <div id="singleCountry">
                <select id="country">
                    <option value="US">🇺🇸 United States</option>
                    <option value="CA">🇨🇦 Canada</option>
                    <option value="UK">🇬🇧 United Kingdom</option>
                    <option value="DE">🇩🇪 Germany</option>
                    <option value="FR">🇫🇷 France</option>
                    <option value="IN">🇮🇳 India</option>
                    <option value="JP">🇯🇵 Japan</option>
                    <option value="AU">🇦🇺 Australia</option>
                    <option value="BR">🇧🇷 Brazil</option>
                    <option value="SG">🇸🇬 Singapore</option>
                </select>
            </div>
            
            <div id="multiCountry" class="multi-country" style="display: none;">
                <h3>Select Countries:</h3>
                <div class="country-grid">
                    <label class="country-checkbox"><input type="checkbox" value="US" checked> 🇺🇸 US</label>
                    <label class="country-checkbox"><input type="checkbox" value="CA"> 🇨🇦 Canada</label>
                    <label class="country-checkbox"><input type="checkbox" value="UK"> 🇬🇧 UK</label>
                    <label class="country-checkbox"><input type="checkbox" value="DE"> 🇩🇪 Germany</label>
                    <label class="country-checkbox"><input type="checkbox" value="FR"> 🇫🇷 France</label>
                    <label class="country-checkbox"><input type="checkbox" value="IN"> 🇮🇳 India</label>
                    <label class="country-checkbox"><input type="checkbox" value="JP"> 🇯🇵 Japan</label>
                    <label class="country-checkbox"><input type="checkbox" value="AU"> 🇦🇺 Australia</label>
                    <label class="country-checkbox"><input type="checkbox" value="BR"> 🇧🇷 Brazil</label>
                    <label class="country-checkbox"><input type="checkbox" value="SG"> 🇸🇬 Singapore</label>
                </div>
            </div>
            
            <div id="results" class="results"></div>
        </div>
        
        <script>
            // Load marketplace information on page load
            window.addEventListener('load', loadMarketplaceInfo);
            
            async function loadMarketplaceInfo() {
                try {
                    const response = await fetch('/api/countries');
                    const data = await response.json();
                    
                    let html = '';
                    for (const [country, info] of Object.entries(data)) {
                        const countryNames = {
                            'US': '🇺🇸 US', 'CA': '🇨🇦 Canada', 'UK': '🇬🇧 UK',
                            'DE': '🇩🇪 Germany', 'FR': '🇫🇷 France', 'IN': '🇮🇳 India',
                            'JP': '🇯🇵 Japan', 'AU': '🇦🇺 Australia', 'BR': '🇧🇷 Brazil', 'SG': '🇸🇬 Singapore'
                        };
                        
                        html += `<div style="margin-bottom: 10px;"><strong>${countryNames[country]}:</strong> `;
                        html += '<div class="marketplaces">';
                        info.marketplaces.forEach(marketplace => {
                            html += `<span class="marketplace-badge">${marketplace}</span>`;
                        });
                        html += '</div></div>';
                    }
                    
                    document.getElementById('marketplace-info').innerHTML = html;
                } catch (error) {
                    console.error('Error loading marketplace info:', error);
                }
            }
            
            document.getElementById('searchType').addEventListener('change', function() {
                const single = document.getElementById('singleCountry');
                const multi = document.getElementById('multiCountry');
                if (this.value === 'multi') {
                    single.style.display = 'none';
                    multi.style.display = 'block';
                } else {
                    single.style.display = 'block';
                    multi.style.display = 'none';
                }
            });
            
            async function searchProducts() {
                const query = document.getElementById('query').value.trim();
                const searchType = document.getElementById('searchType').value;
                const resultsDiv = document.getElementById('results');
                const searchBtn = document.getElementById('searchBtn');
                
                if (!query) {
                    alert('Please enter a product name');
                    return;
                }
                
                if (query.length < 2) {
                    alert('Please enter at least 2 characters');
                    return;
                }
                
                const startTime = performance.now();
                searchBtn.disabled = true;
                searchBtn.textContent = '🔄 Searching...';
                resultsDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>🚀 Scraping multiple marketplaces... This may take 15-30 seconds.</p></div>';
                
                try {
                    let response;
                    
                    if (searchType === 'single') {
                        const country = document.getElementById('country').value;
                        response = await fetch('/api/search', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query, country })
                        });
                    } else {
                        const countries = Array.from(document.querySelectorAll('#multiCountry input:checked')).map(cb => cb.value);
                        if (countries.length === 0) {
                            alert('Please select at least one country');
                            return;
                        }
                        if (countries.length > 5) {
                            alert('Maximum 5 countries allowed for better performance');
                            return;
                        }
                        response = await fetch('/api/search-multi', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ query, countries })
                        });
                    }
                    
                    const data = await response.json();
                    const endTime = performance.now();
                    const duration = ((endTime - startTime) / 1000).toFixed(2);
                    
                    if (data.error) {
                        resultsDiv.innerHTML = `<div class="error">❌ ${data.error}</div>`;
                        return;
                    }
                    
                    displayResults(data, duration, searchType);
                    
                } catch (error) {
                    resultsDiv.innerHTML = '<div class="error">❌ Network error. Please try again. Make sure you have a stable internet connection.</div>';
                    console.error('Search error:', error);
                } finally {
                    searchBtn.disabled = false;
                    searchBtn.textContent = '🔍 Search';
                }
            }
            
            function displayResults(data, duration, searchType) {
                const resultsDiv = document.getElementById('results');
                let html = `<div class="success">✅ Search completed in ${duration}s - Results found via web scraping!</div>`;
                
                if (searchType === 'single') {
                    html += displaySingleCountryResults(data.results);
                } else {
                    html += displayMultiCountryResults(data.results);
                }
                
                resultsDiv.innerHTML = html;
            }
            
            function displaySingleCountryResults(results) {
                if (!results || results.length === 0) {
                    return '<div class="error">No products found. Try different keywords or check your spelling.</div>';
                }
                
                let html = '<div class="product-grid">';
                results.forEach(product => {
                    html += `
                        <div class="product-card">
                            <div class="product-title">${escapeHtml(product.title)}</div>
                            <div class="product-price">${product.currency} ${product.price.toFixed(2)}</div>
                            <div class="product-source">📍 ${product.source}</div>
                            <div class="product-meta">
                                <div><strong>Status:</strong> ${product.availability}</div>
                                <div><strong>Rating:</strong> ${product.rating ? product.rating.toFixed(1) + '/5' : 'N/A'}</div>
                            </div>
                            ${product.shipping_cost ? `<div style="margin-top: 8px; font-size: 0.9em; color: #666;">🚚 Shipping: ${product.currency} ${product.shipping_cost.toFixed(2)}</div>` : ''}
                            <a href="${product.url}" target="_blank" class="product-link">View Product →</a>
                        </div>
                    `;
                });
                html += '</div>';
                return html;
            }
            
            function displayMultiCountryResults(results) {
                let html = '';
                
                for (const [country, products] of Object.entries(results)) {
                    const countryNames = {
                        'US': '🇺🇸 United States', 'CA': '🇨🇦 Canada', 'UK': '🇬🇧 United Kingdom',
                        'DE': '🇩🇪 Germany', 'FR': '🇫🇷 France', 'IN': '🇮🇳 India',
                        'JP': '🇯🇵 Japan', 'AU': '🇦🇺 Australia', 'BR': '🇧🇷 Brazil', 'SG': '🇸🇬 Singapore'
                    };
                    
                    html += `<div class="country-section">`;
                    html += `<div class="country-title">${countryNames[country]} (${products.length} results)</div>`;
                    
                    if (products.length > 0) {
                        html += '<div class="product-grid">';
                        products.slice(0, 8).forEach(product => {
                            html += `
                                <div class="product-card">
                                    <div class="product-title">${escapeHtml(product.title)}</div>
                                    <div class="product-price">${product.currency} ${product.price.toFixed(2)}</div>
                                    <div class="product-source">📍 ${product.source}</div>
                                    <div class="product-meta">
                                        <div><strong>Status:</strong> ${product.availability}</div>
                                        <div><strong>Rating:</strong> ${product.rating ? product.rating.toFixed(1) + '/5' : 'N/A'}</div>
                                    </div>
                                    ${product.shipping_cost ? `<div style="margin-top: 8px; font-size: 0.9em; color: #666;">🚚 Shipping: ${product.currency} ${product.shipping_cost.toFixed(2)}</div>` : ''}
                                    <a href="${product.url}" target="_blank" class="product-link">View Product →</a>
                                </div>
                            `;
                        });
                        html += '</div>';
                    } else {
                        html += '<p style="color: #666; text-align: center; padding: 20px;">No products found in this country. Try different keywords.</p>';
                    }
                    
                    html += '</div>';
                }
                
                return html;
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            // Enable Enter key search
            document.getElementById('query').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchProducts();
                }
            });
        </script>
    </body>
    </html>
    """)

@app.route('/api/search', methods=['POST'])
async def search_single_country():
    """Search products in a single country"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        country = data.get('country', 'US').upper()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if len(query) < 2:
            return jsonify({'error': 'Query must be at least 2 characters'}), 400
        
        if len(query) > 100:
            return jsonify({'error': 'Query too long (max 100 characters)'}), 400
        
        # Get prices using the aggregator
        results = await aggregator.get_all_prices(query, country)
        
        return jsonify({
            'results': results,
            'total_count': len(results),
            'country': country,
            'query': query,
            'timestamp': time.time(),
            'cache_stats': aggregator.get_cache_stats()
        })
        
    except Exception as e:
        logger.error(f"Single country search error: {e}")
        return jsonify({'error': 'Internal server error. Please try again.'}), 500

@app.route('/api/search-multi', methods=['POST'])
async def search_multiple_countries():
    """Search products in multiple countries"""
    try:
        data = request.json
        query = data.get('query', '').strip()
        countries = data.get('countries', ['US'])
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        if len(query) < 2:
            return jsonify({'error': 'Query must be at least 2 characters'}), 400
        
        if not countries:
            return jsonify({'error': 'At least one country is required'}), 400
        
        if len(countries) > 5:
            return jsonify({'error': 'Maximum 5 countries allowed for better performance'}), 400
        
        # Get prices for multiple countries
        results = await aggregator.get_prices_multiple_countries(query, countries)
        
        return jsonify({
            'results': results,
            'countries': countries,
            'query': query,
            'timestamp': time.time(),
            'cache_stats': aggregator.get_cache_stats()
        })
        
    except Exception as e:
        logger.error(f"Multi-country search error: {e}")
        return jsonify({'error': 'Internal server error. Please try again.'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cache_stats': aggregator.get_cache_stats(),
        'supported_countries': list(MARKETPLACE_CONFIGS.keys()),
        'version': '2.0.0-scraping'
    })

@app.route('/api/countries')
def get_countries():
    """Get supported countries and their marketplaces"""
    country_info = {}
    for country, marketplaces in MARKETPLACE_CONFIGS.items():
        country_info[country] = {
            'marketplaces': list(marketplaces.keys()),
            'currency': list(marketplaces.values())[0].get('currency', 'USD')
        }
    
    return jsonify(country_info)

# Command-line interface for testing
async def cli_search():
    """Command-line interface for testing"""
    print("🚀 Free Price Comparison System - CLI Mode")
    print("✨ No API Keys Required - Pure Web Scraping")
    print("=" * 60)
    
    while True:
        try:
            query = input("\nEnter product name (or 'quit' to exit): ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not query:
                continue
            
            if len(query) < 2:
                print("❌ Query must be at least 2 characters")
                continue
            
            country = input("Enter country code (US, CA, UK, DE, FR, IN, JP, AU, BR, SG): ").strip().upper()
            if not country:
                country = 'US'
            
            if country not in MARKETPLACE_CONFIGS:
                print(f"❌ Unsupported country: {country}")
                print(f"Supported countries: {', '.join(MARKETPLACE_CONFIGS.keys())}")
                continue
            
            print(f"\n🔍 Searching for '{query}' in {country}...")
            print("⏳ This may take 15-30 seconds (web scraping multiple sites)...")
            start_time = time.time()
            
            results = await aggregator.get_all_prices(query, country)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"⚡ Search completed in {duration:.2f}s")
            print(f"📊 Found {len(results)} products")
            print("-" * 80)
            
            if results:
                for i, product in enumerate(results[:10], 1):
                    print(f"{i:2d}. {product['source']:<12} | {product['currency']} {product['price']:>8.2f} | {product['title'][:50]}")
                    if product.get('rating'):
                        print(f"     ⭐ {product['rating']:.1f}/5")
                    if product.get('shipping_cost'):
                        print(f"     🚚 Shipping: {product['currency']} {product['shipping_cost']:.2f}")
                    print(f"     🔗 {product['url']}")
                    print()
                
                if len(results) > 10:
                    print(f"... and {len(results) - 10} more results")
            else:
                print("❌ No products found. Try different keywords.")
                print("💡 Tips:")
                print("   - Use simpler, more common product names")
                print("   - Try brand names (e.g., 'Apple iPhone' instead of 'smartphone')")
                print("   - Check your spelling")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.error(f"CLI search error: {e}")

def run_performance_test():
    """Run a performance test"""
    print("🧪 Running Performance Test...")
    print("=" * 40)
    
    async def test():
        test_queries = ["iPhone 15", "MacBook Air", "Samsung Galaxy S24"]
        test_countries = ["US", "CA", "UK"]
        
        for query in test_queries:
            for country in test_countries:
                print(f"\n🔍 Testing: '{query}' in {country}")
                start_time = time.time()
                
                try:
                    results = await aggregator.get_all_prices(query, country)
                    duration = time.time() - start_time
                    print(f"   ✅ {len(results)} results in {duration:.2f}s")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        # Test cache performance
        print(f"\n📊 Cache Stats: {aggregator.get_cache_stats()}")
    
    asyncio.run(test())

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'cli':
            # Run CLI mode
            asyncio.run(cli_search())
        elif sys.argv[1] == 'test':
            # Run performance test
            run_performance_test()
        else:
            print("Usage:")
            print("  python app.py          # Run web server")
            print("  python app.py cli      # Run CLI mode")
            print("  python app.py test     # Run performance test")
    else:
        # Run web server
        print("🚀 Starting Free Price Comparison System...")
        print("✨ No API Keys Required - Pure Web Scraping")
        print("🌐 Web interface: http://localhost:5000")
        print("📊 API endpoint: http://localhost:5000/api/search")
        print("🏥 Health check: http://localhost:5000/api/health")
        print("🗺️  Countries: http://localhost:5000/api/countries")
        print("-" * 60)
        print("💡 Tips for better results:")
        print("   - Use specific product names (e.g., 'iPhone 15 Pro' vs 'phone')")
        print("   - Include brand names when possible")
        print("   - Be patient - web scraping takes 15-30 seconds")
        print("   - Results are cached for 30 minutes")
        print("-" * 60)
        
        try:
            app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
        except KeyboardInterrupt:
            print("\n👋 Server stopped. Goodbye!")
        except Exception as e:
            print(f"❌ Server error: {e}")
            logger.error(f"Server startup error: {e}")