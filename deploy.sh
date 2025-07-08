#!/bin/bash

echo "🚀 Deploying Price Comparison Tool..."

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Building Docker image..."
    docker build -t price-comparison-tool .
    
    echo "🏃 Running container..."
    docker run -d -p 5000:5000 --name price-tool price-comparison-tool
    
    echo "✅ Deployment complete! App running at http://localhost:5000"
else
    echo "🐍 Running with Python..."
    pip install -r requirements.txt
    python app.py &
    
    echo "✅ Deployment complete! App running at http://localhost:5000"
fi
