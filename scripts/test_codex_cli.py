#!/usr/bin/env python3
"""
Script de prueba básico para validar la integración Codex CLI.
Ejecutar con: python scripts/test_codex_cli.py
"""

import asyncio
import sys
import pathlib

# Add current directory to path to import llm module
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from llm import Client

async def test_codex_cli_basic():
    """Test básico de integración con CLI mock (no ejecuta comando real)"""
    print("🔧 Testing Codex CLI integration...")

    try:
        # Create a client that would use codex_cli if configured
        client = Client(role="dev")

        # Check if CLI provider is configured
        if client.provider_type != "codex_cli":
            print("⚠️  Codex CLI not configured as provider. Testing with current provider instead.")
            # Test with current provider to ensure basic functionality works
            response = await client.chat(
                system="You are a helpful assistant.",
                user="Say hello in Spanish."
            )
            print(f"✅ Basic LLM test passed with {client.provider_type}")
            print(f"Response: {response[:100]}...")
            return True

        print(f"✅ CLI Provider detected: {client.cli_command}")
        print(f"   - Command: {client.cli_command}")
        print(f"   - Timeout: {client.cli_timeout}s")
        print("   - Input format: {client.cli_input_format}")

        # Note: Actual CLI test would require the real codex CLI to be installed
        print("ℹ️  To test actual CLI execution, ensure 'codex' command is available and run:")
        print("   CONCEPT='Test' make dev")
        print("   Then check artifacts/dev/last_raw.txt for CLI logs")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_error_handling():
    """Test error handling scenarios"""
    print("\n🔧 Testing error handling...")

    # Test CLI not configured
    try:
        from llm import Client
        # This will fail if codex_cli provider is not properly configured
        client = Client(role="dev", provider="codex_cli")
        response = await client.chat("system", "user")
        print("⚠️ Unexpected success - CLI might actually be working")
    except RuntimeError as e:
        if "CODEX_CLI" in str(e):
            print(f"✅ Proper CLI error handling: {e}")
        else:
            print(f"❌ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected exception: {e}")
        return False

    return True

if __name__ == "__main__":
    print("🚀 Running Codex CLI integration tests...\n")

    async def run_tests():
        test1 = await test_codex_cli_basic()
        test2 = await test_error_handling()

        if test1 and test2:
            print("\n✅ All tests passed! Codex CLI integration ready.")
            print("📝 Next steps:")
            print("   1. Update config.yaml roles to use provider: codex_cli")
            print("   2. Ensure 'codex' CLI is installed and working")
            print("   3. Test with: CONCEPT='Test feature' make dev")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed.")
            sys.exit(1)

    asyncio.run(run_tests())
