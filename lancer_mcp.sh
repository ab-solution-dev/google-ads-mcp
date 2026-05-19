#!/bin/bash

# ── Lancement MCP Google Ads + Ngrok ─────────────────────────────────────────
cd ~/Documents/googleads-mcp

echo "🚀 Lancement du serveur MCP Google Ads..."
source venv/bin/activate
python server.py &
MCP_PID=$!

sleep 2

echo "🌐 Lancement du tunnel Ngrok..."
ngrok http 8080 &
NGROK_PID=$!

echo ""
echo "✅ Les deux serveurs sont lancés !"
echo "   MCP PID   : $MCP_PID"
echo "   Ngrok PID : $NGROK_PID"
echo ""
echo "   URL Ngrok : https://barrette-clarity-consonant.ngrok-free.app/sse"
echo ""
echo "   Appuie sur Entrée pour tout arrêter..."
read

kill $MCP_PID $NGROK_PID 2>/dev/null
echo "🛑 Serveurs arrêtés."
