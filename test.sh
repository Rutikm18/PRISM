#!/bin/bash

echo "🧪 Testing Price Comparison Tool..."

# Test 1: Health check
echo "📋 Testing health endpoint..."
curl -s http://localhost:5000/health | jq '.'

# Test 2: US iPhone search
echo "📱 Testing US iPhone search..."
curl -s -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"country": "US", "query": "iPhone 16 Pro, 128GB"}' | jq '.total_count'

# Test 3: India boAt search
echo "🎧 Testing India boAt search..."
curl -s -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"country": "IN", "query": "boAt Airdopes 311 Pro"}' | jq '.total_count'

echo "✅ Tests completed!"
