#!/bin/bash

echo "🚀 Setting up AI Red Team in AutoGen Studio..."

# Install AutoGen Studio
pip install autogenstudio

# Create config directory
mkdir -p ~/.autogenstudio/configs

# Download configuration (replace with your URL)
curl -o ~/.autogenstudio/configs/redteam-agents.json \
  https://raw.githubusercontent.com/your-repo/main/redteam-agents.json

# Or create it locally
cat > ~/.autogenstudio/configs/redteam-agents.json << 'EOF'
[paste entire JSON here]
EOF

# Start AutoGen Studio
echo "📦 Starting AutoGen Studio..."
autogenstudio ui --port 8080 &

# Wait for startup
sleep 5

# Import configuration
echo "📥 Importing Red Team configuration..."
autogenstudio import --file ~/.autogenstudio/configs/redteam-agents.json --type all

echo "✅ Setup complete! Access at http://localhost:8080"
echo "📚 Quick Start:"
echo "   1. Go to 'Build' tab"
echo "   2. Select 'StandardPentest' workflow"
echo "   3. Click 'Run' and enter target: demo.vulnerable.com"
