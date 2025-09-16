#!/bin/bash
echo "🔍 Quick WSL Backend Check"
echo "========================="

echo "Current directory: $(pwd)"
echo "Backend directory: $([ -d "backend" ] && echo "✅ Exists" || echo "❌ Missing")"

echo ""
echo "🐍 Python Check:"
if command -v python3 &> /dev/null; then
    echo "✅ Python3: $(python3 --version)"
else
    echo "❌ Python3 not found"
fi

echo ""
echo "📦 Virtual Environment Check:"
if [ -d "backend/venv" ]; then
    echo "✅ Virtual environment exists"
    cd backend
    source venv/bin/activate
    echo "✅ Virtual environment activated"
    echo "Python in venv: $(which python)"
    cd ..
else
    echo "❌ Virtual environment missing"
fi

echo ""
echo "🐳 Ollama Check:"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama accessible"
else
    echo "❌ Ollama not accessible"
fi

echo ""
echo "🚀 Try to start backend manually:"
echo "cd backend && source venv/bin/activate && python start_backend.py"
