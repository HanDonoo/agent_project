#!/bin/bash
# Test script for EC Skills Finder API

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       EC Skills Finder API - Test Suite                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://localhost:8001"

# Test 1: Health Check
echo "=== Test 1: Health Check ==="
curl -s $BASE_URL/health | python3 -m json.tool
echo ""
echo ""

# Test 2: List Models
echo "=== Test 2: List Models (OpenWebUI) ==="
curl -s $BASE_URL/v1/models | python3 -m json.tool
echo ""
echo ""

# Test 3: Direct Query
echo "=== Test 3: Direct Query - Python Expert ==="
curl -s -X POST $BASE_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Find me a Python expert", "top_n": 3}' \
  | python3 -m json.tool | head -80
echo ""
echo ""

# Test 4: Chat Completions
echo "=== Test 4: Chat Completions (OpenWebUI) - Network Engineer ==="
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ec-skills-finder",
    "messages": [
      {"role": "user", "content": "I need a network engineer with MPLS experience"}
    ]
  }' | python3 -m json.tool | grep -A 50 '"content"' | head -60
echo ""
echo ""

# Test 5: Complex Query
echo "=== Test 5: Complex Query - Machine Learning ==="
curl -s -X POST $BASE_URL/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ec-skills-finder",
    "messages": [
      {"role": "user", "content": "Find someone who can build a deep learning pipeline"}
    ]
  }' | python3 -m json.tool | grep -A 50 '"content"' | head -60
echo ""
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Tests Complete                          ║"
echo "╚════════════════════════════════════════════════════════════╝"

