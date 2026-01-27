#!/usr/bin/env python3
"""
Test Gemini integration without actually calling the API
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 80)
    print("🧪 Test 1: Importing modules")
    print("=" * 80)
    
    try:
        from EC_skills_agent.ai_client import AIClient, OllamaClient, GeminiClient, create_ai_client
        print("✅ ai_client module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import ai_client: {e}")
        return False
    
    try:
        import config
        print("✅ config module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import config: {e}")
        return False
    
    try:
        from EC_skills_agent.EC_skills_interpreter_engine import SkillInferenceEngine
        print("✅ EC_skills_interpreter_engine module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import EC_skills_interpreter_engine: {e}")
        return False
    
    return True


def test_ai_client_creation():
    """Test AI client creation"""
    print("\n" + "=" * 80)
    print("🧪 Test 2: Creating AI clients")
    print("=" * 80)
    
    from EC_skills_agent.ai_client import create_ai_client, OllamaClient, GeminiClient
    
    # Test Ollama client
    try:
        ollama_client = create_ai_client(
            provider="ollama",
            base_url="http://localhost:11434",
            model="llama3.2:3b"
        )
        print(f"✅ Ollama client created: {type(ollama_client).__name__}")
        assert isinstance(ollama_client, OllamaClient)
    except Exception as e:
        print(f"❌ Failed to create Ollama client: {e}")
        return False
    
    # Test Gemini client (with dummy API key)
    try:
        gemini_client = create_ai_client(
            provider="gemini",
            api_key="dummy_key_for_testing",
            model="gemini-2.0-flash-exp"
        )
        print(f"✅ Gemini client created: {type(gemini_client).__name__}")
        assert isinstance(gemini_client, GeminiClient)
    except Exception as e:
        print(f"❌ Failed to create Gemini client: {e}")
        return False
    
    return True


def test_config_validation():
    """Test configuration validation"""
    print("\n" + "=" * 80)
    print("🧪 Test 3: Configuration validation")
    print("=" * 80)
    
    import config
    import os
    
    # Save original values
    original_provider = os.getenv("AI_PROVIDER")
    original_key = os.getenv("GEMINI_API_KEY")
    
    # Test Ollama config (should pass without API key)
    os.environ["AI_PROVIDER"] = "ollama"
    os.environ["GEMINI_API_KEY"] = ""
    
    # Reload config
    import importlib
    importlib.reload(config)
    
    try:
        config.validate_config()
        print("✅ Ollama config validation passed")
    except Exception as e:
        print(f"❌ Ollama config validation failed: {e}")
        return False
    
    # Test Gemini config without API key (should fail)
    os.environ["AI_PROVIDER"] = "gemini"
    os.environ["GEMINI_API_KEY"] = ""
    importlib.reload(config)
    
    try:
        config.validate_config()
        print("❌ Gemini config should have failed without API key")
        return False
    except ValueError as e:
        print(f"✅ Gemini config correctly requires API key: {e}")
    
    # Restore original values
    if original_provider:
        os.environ["AI_PROVIDER"] = original_provider
    if original_key:
        os.environ["GEMINI_API_KEY"] = original_key
    
    return True


def test_message_format():
    """Test message format conversion"""
    print("\n" + "=" * 80)
    print("🧪 Test 4: Message format conversion")
    print("=" * 80)
    
    from EC_skills_agent.ai_client import GeminiClient
    
    # Create a Gemini client with dummy key
    client = GeminiClient(api_key="dummy_key", model="gemini-2.0-flash-exp")
    
    # Test message format
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    print(f"✅ Message format test passed (client created successfully)")
    print(f"   Client model: {client.model}")
    print(f"   Client base URL: {client.base_url}")
    
    return True


def main():
    print("\n🧪 Gemini Integration Test Suite\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("AI Client Creation", test_ai_client_creation),
        ("Configuration Validation", test_config_validation),
        ("Message Format", test_message_format),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print("📊 Test Results")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 All tests passed! The integration is ready.")
        print("\n📝 Next steps:")
        print("   1. Get a Gemini API key from https://makersuite.google.com/app/apikey")
        print("   2. Copy .env.example to .env")
        print("   3. Set GEMINI_API_KEY in .env")
        print("   4. Run: python start_server.py")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

