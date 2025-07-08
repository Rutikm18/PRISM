# Universal Price Comparison Tool

A comprehensive, AI-powered price comparison tool that fetches product prices from multiple websites across different countries. This tool automatically discovers relevant e-commerce sites for each country and uses intelligent matching to ensure product relevance.

## 🌟 Features

- **Multi-Country Support**: Supports 10+ countries including US, India, UK, Canada, Australia, Germany, France, Japan, Singapore, and Brazil
- **Intelligent Website Discovery**: Automatically selects relevant e-commerce websites for each country
- **AI-Powered Product Matching**: Uses advanced matching algorithms to ensure product relevance
- **Concurrent Processing**: Asynchronous scraping for maximum speed
- **Price Sorting**: Results automatically sorted by price (lowest to highest)
- **Rich Product Information**: Includes price, currency, availability, ratings, and direct links
- **Web Interface**: User-friendly web interface for easy searching
- **REST API**: RESTful API for programmatic access
- **Docker Support**: Fully containerized for easy deployment

## 🚀 Quick Start

### Method 1: Using the Setup Script (Recommended)
```bash
# Download and run the setup script
curl -sSL https://raw.githubusercontent.com/yourusername/price-comparison-tool/main/setup.sh | bash

# Or if you have the script locally:
chmod +x setup.sh
./setup.sh
```

### Method 2: Manual Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/price-comparison-tool.git
cd price-comparison-tool

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Method 3: Docker
```bash
# Build and run with Docker
docker build -t price-comparison-tool .
docker run -p 5000:5000 price-comparison-tool

# Or use docker-compose
docker-compose up --build
```

## 📋 Usage

### Web Interface
1. Open your browser and go to `http://localhost:5000`
2. Select your country from the dropdown
3. Enter your product search query (e.g., "iPhone 16 Pro, 128GB")
4. Click "Search Products"
5. View results sorted by price

### API Usage

#### Search Products
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "country": "US",
    "query": "iPhone 16 Pro, 128GB"
  }'
```

#### Example Response
```json
{
  "results": [
    {
      "link": "https://amazon.com/product/...",
      "price": "999",
      "currency": "$",
      "productName": "Apple iPhone 16 Pro 128GB",
      "website": "amazon.com",
      "availability": "In Stock",
      "rating": "4.5/5"
    }
  ],
  "total_count": 15,
  "country": "US",
  "query": "iPhone 16 Pro, 128GB"
}
```

#### Health Check
```bash
curl http://localhost:5000/health
```

## 🧪 Testing

### Test with Example Queries

#### US Query - iPhone
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "country": "US",
    "query": "iPhone 16 Pro, 128GB"
  }'
```

#### India Query - boAt Earphones
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "country": "IN",
    "query": "boAt Airdopes 311 Pro"
  }'
```

## 🌍 Supported Countries & Websites

| Country | Code | Major Websites Covered |
|---------|------|----------------------|
| United States | US | Amazon, Walmart, Best Buy, Target, Newegg |
| India | IN | Amazon.in, Flipkart, Snapdeal, Croma, Sangeetha Mobiles |
| United Kingdom | UK | Amazon.co.uk, Currys, Argos, John Lewis |
| Canada | CA | Amazon.ca, Best Buy CA, Canada Computers |
| Australia | AU | Amazon.com.au, JB Hi-Fi, Harvey Norman |
| Germany | DE | Amazon.de, Otto, Saturn, MediaMarkt |
| France | FR | Amazon.fr, Fnac, Darty, Boulanger |
| Japan | JP | Amazon.co.jp, Rakuten, Yodobashi |
| Singapore | SG | Amazon.sg, Lazada, Shopee, Qoo10 |
| Brazil | BR | Amazon.com.br, Mercado Livre, Magazine Luiza |

## 🏗️ Architecture

The tool consists of several key components:

1. **CountryWebsiteMapper**: Maps countries to relevant e-commerce websites
2. **WebScraper**: Handles concurrent web scraping with proper headers and error handling
3. **ProductParser**: Extracts product information from different website structures
4. **SearchEngine**: Orchestrates the search across multiple websites
5. **AIProductMatcher**: Uses AI algorithms to filter relevant products
6. **Flask API**: Provides REST endpoints and web interface

## 🔧 Configuration

### Environment Variables
- `FLASK_ENV`: Set to 'production' for production deployment
- `PORT`: Port number for the application (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: False in production)

### Customizing Website Lists
You can modify the `WEBSITE_MAP` in `CountryWebsiteMapper` class to add or remove websites for specific countries.

## 📊 Performance Features

- **Concurrent Processing**: Multiple websites scraped simultaneously
- **Intelligent Caching**: Reduces redundant requests
- **Rate Limiting**: Respects website rate limits
- **Error Handling**: Graceful handling of failed requests
- **Timeout Management**: Prevents hanging requests

## 🚀 Deployment Options

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

### Heroku Deployment
```bash
# Create Procfile
echo "web: gunicorn app:app" > Procfile

# Deploy to Heroku
heroku create your-app-name
git push heroku main
```

### Railway Deployment
```bash
# Deploy to Railway
railway login
railway init
railway up
```

## 🛠️ Development

### Running in Development Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Adding New Countries
1. Add country code and websites to `WEBSITE_MAP` in `CountryWebsiteMapper`
2. Add currency symbol to `currency_symbols` in `ProductParser`
3. Test with sample queries

### Adding New Website Parsers
1. Add website-specific selectors to `SITE_SELECTORS` in `ProductParser`
2. Update `extract_site_type` method to recognize the new website
3. Add search URL pattern to `_generate_search_urls` in `SearchEngine`

## 📝 API Documentation

### Endpoints

#### POST /api/search
Search for products across multiple websites.

**Request Body:**
```json
{
  "country": "US",
  "query": "product search terms"
}
```

**Response:**
```json
{
  "results": [
    {
      "link": "product_url",
      "price": "price_value",
      "currency": "currency_symbol",
      "productName": "product_name",
      "website": "website_domain",
      "availability": "availability_status",
      "rating": "rating_value"
    }
  ],
  "total_count": 10,
  "country": "US",
  "query": "search_query"
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Issue**: No results found
**Solution**: Check if the product exists on supported websites for the selected country

**Issue**: Slow response times
**Solution**: Reduce the number of websites searched or implement caching

**Issue**: Rate limiting errors
**Solution**: Implement delays between requests or use rotating proxies

### Support

For support, please open an issue on GitHub or contact the maintainers.

## 🔮 Future Enhancements

- [ ] Price history tracking
- [ ] Email price alerts
- [ ] Mobile app
- [ ] More sophisticated AI matching
- [ ] Proxy rotation for better reliability
- [ ] Database storage for caching
- [ ] User accounts and favorites
- [ ] Price comparison charts
- [ ] Integration with more countries
- [ ] Real-time price monitoring

---

**Note**: This tool is for educational and personal use. Please respect websites' robots.txt and terms of service.
