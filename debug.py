# debug_flask.py - Debug Flask App Startup Issues
import sys
import os

print("🔍 Debugging Flask App Startup...")
print("=" * 50)

# Check if we can import Flask
try:
    from flask import Flask
    print("✅ Flask imported successfully")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    print("💡 Install Flask: pip install flask flask-cors")
    sys.exit(1)

# Check if we can import our modules
try:
    print("🧪 Testing our module imports...")
    from config_global_price import MARKETPLACE_CONFIGS
    from marketplace_apis import AmazonScraper
    from global_price_aggregator import GlobalPriceAggregator
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Module import failed: {e}")
    sys.exit(1)

# Test basic Flask app
try:
    print("🧪 Testing basic Flask app...")
    app = Flask(__name__)
    
    @app.route('/')
    def hello():
        return "✅ Flask is working!"
    
    @app.route('/test')
    def test():
        return {"status": "working", "message": "API endpoints work!"}
    
    print("✅ Flask app created successfully")
    
    # Try to run the app
    print("\n🚀 Starting Flask development server...")
    print("📍 URL: http://localhost:5000")
    print("📍 Test URL: http://localhost:5000/test")
    print("⚠️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
    
except Exception as e:
    print(f"❌ Flask app failed to start: {e}")
    print("\n🔧 Troubleshooting steps:")
    print("1. Check if port 5000 is already in use")
    print("2. Try a different port: app.run(port=8080)")
    print("3. Check firewall settings")
    print("4. Make sure you have admin privileges")