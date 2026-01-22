#!/bin/bash
# EC_Proj Setup Script
# Run this script after cloning the repository

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       EC Skills Finder - Initial Setup                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   ✅ Python $python_version"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "   ✅ Virtual environment created"
else
    echo "📦 Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate
echo "   ✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
echo "   ✅ pip upgraded"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt
echo "   ✅ Dependencies installed"
echo ""

# Fix urllib3 compatibility issue for macOS
echo "🔧 Fixing urllib3 compatibility (macOS)..."
pip install 'urllib3<2.0' > /dev/null 2>&1
echo "   ✅ urllib3 downgraded to compatible version"
echo ""

# Check if database exists
if [ -f "data/employee_directory_200_mock.db" ]; then
    echo "💾 Database already exists"
    db_size=$(ls -lh data/employee_directory_200_mock.db | awk '{print $5}')
    echo "   ℹ️  Database size: $db_size"
    echo ""
    
    read -p "   Do you want to regenerate the database? (y/N): " regenerate
    if [[ $regenerate =~ ^[Yy]$ ]]; then
        echo "   🔄 Regenerating database..."
        cd data_creation
        python3 create_new_db_with_mock_data.py
        cd ..
        echo "   ✅ Database regenerated"
    else
        echo "   ⏭️  Skipping database regeneration"
    fi
else
    echo "💾 Generating database with mock data..."
    cd data_creation
    python3 create_new_db_with_mock_data.py
    cd ..
    echo "   ✅ Database created successfully"
fi
echo ""

# Run setup check
echo "🔍 Running setup verification..."
python3 tests/check_setup.py
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Setup Complete! 🎉                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Next steps:"
echo "   1. Activate virtual environment: source .venv/bin/activate"
echo "   2. Start Ollama: ollama serve"
echo "   3. Pull model: ollama pull llama3.1:8b"
echo "   4. Start server: python start_server.py"
echo ""
echo "📚 Documentation:"
echo "   - Quick Start: cat QUICKSTART.md"
echo "   - Full Docs: cat README.md"
echo ""

