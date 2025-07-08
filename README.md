# 🔥 Free Price Comparison System

A lightning-fast, **100% FREE** price comparison system that scrapes multiple marketplaces without requiring any API keys!

## ✨ Features

- **🆓 Completely Free** - No API keys, no subscriptions, no hidden costs
- **🌍 Global Support** - 10 countries, 25+ marketplaces
- **⚡ Fast Results** - Concurrent scraping with intelligent caching
- **🎯 Smart Deduplication** - Removes duplicate products automatically
- **📱 Responsive Design** - Works on desktop, tablet, and mobile
- **🔒 Rate Limited** - Respectful scraping that won't get blocked

## 🌐 Supported Countries & Marketplaces

| Country | Marketplaces |
|---------|-------------|
| 🇺🇸 United States | Amazon, eBay, Walmart, Target, Newegg, Etsy |
| 🇨🇦 Canada | Amazon, eBay, Walmart, Newegg, Best Buy |
| 🇬🇧 United Kingdom | Amazon, eBay, Argos, Tesco |
| 🇩🇪 Germany | Amazon, eBay, Otto, MediaMarkt |
| 🇫🇷 France | Amazon, eBay, Fnac, Cdiscount |
| 🇮🇳 India | Amazon, Flipkart, Snapdeal, Myntra, Ajio |
| 🇯🇵 Japan | Amazon, Rakuten, Yahoo Shopping, Mercari |
| 🇦🇺 Australia | Amazon, eBay, JB Hi-Fi, Kmart |
| 🇧🇷 Brazil | Amazon, MercadoLibre, Magazine Luiza, Casas Bahia |
| 🇸🇬 Singapore | Amazon, Lazada, Shopee, Qoo10 |

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Make sure you have Python 3.8+ installed
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# Start the web server
python app.py

# Or run in CLI mode
python app.py cli

# Or run performance tests
python app.py test
```

### 3. Access the Web Interface

Open your browser and go to: `http://localhost:5000`

## 📖 Usage Examples

### Web Interface
1. Open `http://localhost:5000` in your browser
2. Enter a product name (e.g., "iPhone 15 Pro")
3. Select single country or multiple countries
4. Click "Search" and wait 15-30 seconds
5. Browse results sorted by price

### CLI Mode
```bash
python app.py cli

# Example session:
Enter product name: iPhone 15 Pro
Enter country code: US
🔍 Searching for 'iPhone 15 Pro' in US...
⚡ Search completed in 23.4s
📊 Found 12 products
```

### API Usage
```bash
# Single country search
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "MacBook Air M2", "country": "US"}'

# Multiple countries search
curl -X POST http://localhost:5000/api/search-multi \
  -H "Content-Type: application/json" \
  -d '{"query": "Samsung Galaxy S24", "countries": ["US", "CA", "UK"]}'
```

## 🏗️ Architecture

### Core Components

1. **Marketplace Scrapers** (`marketplace_apis.py`)
   - Individual scrapers for each marketplace
   - Intelligent HTML parsing with multiple selectors
   - Rate limiting and error handling

2. **Price Aggregator** (`global_price_aggregator.py`)
   - Coordinates multiple scrapers
   - Handles caching and deduplication
   - Manages concurrent requests

3. **Web Interface** (`app.py`)
   - Flask web server
   - RESTful API endpoints
   - Modern responsive UI

4. **Configuration** (`config_global_price.py`)
   - Marketplace configurations
   - Rate limiting settings
   - User agent rotation

### Data Flow

```
User Query → Cache Check → Concurrent Scrapers → Parse Results → 
Deduplicate → Sort by Price → Cache Results → Return to User
```

## ⚙️ Configuration

### Rate Limiting
The system uses respectful rate limiting to avoid being blocked:

```python
RATE_LIMITS = {
    'amazon': {'requests_per_second': 0.5, 'burst': 2},
    'ebay': {'requests_per_second': 1, 'burst': 3},
    'walmart': {'requests_per_second': 1, 'burst': 3},
    # ... more configurations
}
```

### Caching
Results are cached for 30 minutes to improve performance:

```python
CACHE_CONFIG = {
    'default_ttl': 1800,  # 30 minutes
    'max_size': 5000,
    'cleanup_interval': 3600  # 1 hour
}
```

### User Agent Rotation
Multiple user agents are rotated to avoid detection:

```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36...',
    # ... more user agents
]
```

## 🛠️ Troubleshooting

### Common Issues

**Slow Response Times**
- Web scraping takes 15-30 seconds - this is normal
- Use single country searches for faster results
- Results are cached for subsequent searches

**No Results Found**
- Try simpler, more common product names
- Include brand names (e.g., "Apple iPhone" vs "smartphone")
- Check spelling and try different keywords

**Connection Errors**
- Check your internet connection
- Some sites may temporarily block requests
- Try again in a few minutes

**Installation Issues**
```bash
# If you get compilation errors, try:
pip install --only-binary=all -r requirements.txt

# On Windows, you might need:
pip install --upgrade pip setuptools wheel
```

### Performance Tips

1. **Use Specific Queries**: "iPhone 15 Pro 128GB" works better than "phone"
2. **Limit Countries**: Search 1-3 countries at a time for faster results
3. **Cache Utilization**: Identical searches within 30 minutes use cached results
4. **Network**: Ensure stable internet connection for reliable scraping

## 📊 API Endpoints

### Search Single Country
```
POST /api/search
{
  "query": "product name",
  "country": "US"
}
```

### Search Multiple Countries
```
POST /api/search-multi
{
  "query": "product name", 
  "countries": ["US", "CA", "UK"]
}
```

### Health Check
```
GET /api/health
```

### Get Supported Countries
```
GET /api/countries
```

### Clear Cache
```
POST /api/cache/clear
```

## 🚨 Legal Notice

This tool is for educational and personal use only. Please:

- ✅ Use responsibly and respect website terms of service
- ✅ Don't make excessive requests (rate limiting is built-in)
- ✅ Use for personal price comparison only
- ❌ Don't use for commercial data harvesting
- ❌ Don't circumvent rate limiting

## 🤝 Contributing

Want to add more marketplaces or countries? Here's how:

1. **Add to Configuration** (`config_global_price.py`):
```python
'NEW_COUNTRY': {
    'marketplace': {'domain': 'example.com', 'currency': 'USD'}
}
```

2. **Create Scraper** (`marketplace_apis.py`):
```python
class NewMarketplaceScraper(BaseScraper):
    # Implement scraping logic
```

3. **Update Aggregator** (`global_price_aggregator.py`):
```python
# Add to get_all_prices method
if 'new_marketplace' in marketplaces:
    tasks.append(self.new_scraper.search_products(query, country, client))
```

## 📈 Future Enhancements

- 🔍 **More Marketplaces**: Adding Alibaba, AliExpress, etc.
- 🌏 **More Countries**: Expanding to Asia, Europe, Latin America
- 📱 **Mobile App**: React Native or Flutter app
- 🔔 **Price Alerts**: Email/SMS notifications for price drops
- 📊 **Analytics**: Price history and trend analysis
- 🤖 **AI Integration**: Smart product matching and recommendations

## 📄 License

MIT License - Feel free to use, modify, and distribute!

## 🙋‍♂️ Support

- 🐛 **Bug Reports**: Create an issue with detailed description
- 💡 **Feature Requests**: Explain your use case and requirements  
- 📚 **Documentation**: Check this README and code comments
- ⚡ **Performance**: Check network connection and try simpler queries

---

**Happy Price Hunting! 🛒💰**