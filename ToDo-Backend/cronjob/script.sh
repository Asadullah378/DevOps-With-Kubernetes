#!/bin/sh
set -e

# Get random Wikipedia article URL from redirect location header
WIKI_URL=$(curl -sI "https://en.wikipedia.org/wiki/Special:Random" | grep -i "^location:" | tr -d '\r' | cut -d' ' -f2)

echo "Random Wikipedia URL: $WIKI_URL"

# Create todo via backend API
TODO_TEXT="Read $WIKI_URL"

curl -X POST "$BACKEND_URL/todos" \
  -H "Content-Type: application/json" \
  -d "{\"todo\": \"$TODO_TEXT\"}"

echo ""
echo "Todo created successfully!"

