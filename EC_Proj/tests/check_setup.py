#!/usr/bin/env python3
"""
Check if EC Skills Finder is ready to run
"""
import sys
import subprocess
from pathlib import Path
import requests

def check_python_version():
    """Check Python version"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (need 3.9+)")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking Python dependencies...")
    required = ["fastapi", "uvicorn", "pydantic", "requests"]
    all_ok = True
    
    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} (run: pip install -r requirements.txt)")
            all_ok = False
    
    return all_ok

def check_database():
    """Check if database exists"""
    print("\n💾 Checking database...")
    db_path = Path(__file__).parent / "data" / "employee_directory_200_mock.db"
    
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ Database found ({size_mb:.2f} MB)")
        return True
    else:
        print(f"   ❌ Database not found at: {db_path}")
        print(f"      Run: cd data_creation && python create_new_db_with_mock_data.py")
        return False

def check_ollama():
    """Check if Ollama is running"""
    print("\n🤖 Checking Ollama...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"   ✅ Ollama is running")
            
            # Check for llama3.1:8b
            has_model = any("llama3.1" in m.get("name", "") for m in models)
            if has_model:
                print(f"   ✅ llama3.1:8b model found")
                return True
            else:
                print(f"   ⚠️  llama3.1:8b model not found")
                print(f"      Run: ollama pull llama3.1:8b")
                return False
        else:
            print(f"   ❌ Ollama returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print(f"   ❌ Ollama not running at http://localhost:11434")
        print(f"      Start with: ollama serve")
        print(f"      Or: docker-compose up -d ollama")
        return False

def check_port():
    """Check if port 8001 is available"""
    print("\n🔌 Checking port 8001...")
    try:
        result = subprocess.run(
            ["lsof", "-ti:8001"],
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            print(f"   ⚠️  Port 8001 is in use (PID: {result.stdout.strip()})")
            print(f"      Kill with: lsof -ti:8001 | xargs kill -9")
            return False
        else:
            print(f"   ✅ Port 8001 is available")
            return True
    except FileNotFoundError:
        print(f"   ⚠️  Cannot check port (lsof not found)")
        return True

def main():
    """Run all checks"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       EC Skills Finder - Setup Check                      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    checks = [
        ("Python Version", check_python_version()),
        ("Dependencies", check_dependencies()),
        ("Database", check_database()),
        ("Ollama", check_ollama()),
        ("Port 8001", check_port()),
    ]
    
    print("\n" + "="*60)
    print("📊 Summary")
    print("="*60)
    
    all_passed = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All checks passed! Ready to start the server.")
        print("\n🚀 Run: python start_server.py")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\n📚 See QUICKSTART.md for help")
    
    print()
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

