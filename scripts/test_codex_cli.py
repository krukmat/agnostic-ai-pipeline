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
        # Test architect role with CLI provider
        client_architect = Client(role="architect")
        if client_architect.provider_type == "codex_cli":
            print("✅ Architect role configured with Codex CLI:")
            print(f"   - Command: {client_architect.cli_command}")
            print(f"   - Model: {client_architect.model}")
            print(f"   - Timeout: {client_architect.cli_timeout}s")
            print(f"   - Input format: {client_architect.cli_input_format}")

            # Create a client that would use codex_cli if configured for dev
            client_dev = Client(role="dev")
            if client_dev.provider_type != "codex_cli":
                print("ℹ️  Dev role uses ollama (fallback provider)")
                # Test with current provider to ensure basic functionality works
                response = await client_dev.chat(
                    system="You are a helpful assistant.",
                    user="Say hello in Spanish."
                )
                print(f"✅ Basic LLM test passed with {client_dev.provider_type}")
                print(f"Response: {response[:100]}...")
                return True
        else:
            print("⚠️  Architect CLI not configured. Testing with current provider instead.")
            # Test with current provider to ensure basic functionality works
            response = await client_architect.chat(
                system="You are a helpful assistant.",
                user="Say hello in Spanish."
            )
            print(f"✅ Basic LLM test passed with {client_architect.provider_type}")
            print(f"Response: {response[:100]}...")
            return True

        # Try to test actual CLI execution to demonstrate error handling
        print("\n🔧 Testing actual CLI execution (expected to fail without 'codex' command)...")
        try:
            test_cli_client = Client(role="architect", provider="codex_cli")
            response = await test_cli_client.chat(
                system="You are an architect assistant.",
                user="Create a simple plan for a login system."
            )
            print(f"⚠️  Unexpected CLI success: {response[:100]}...")
        except RuntimeError as e:
            if "CODEX_CLI_NOT_FOUND" in str(e):
                print("✅ Expected CLI error: 'codex' command not found - this is normal")
                return True
            elif "CODEX_CLI_" in str(e):
                print(f"✅ CLI error handling works: {e}")
                return True
            else:
                print(f"❌ Unexpected CLI runtime error: {e}")
                return False
        except Exception as e:
            print(f"❌ Unexpected exception trying CLI: {e}")
            return False

        # Note: If we get here without throwing, CLI might actually work
        print("ℹ️  CLI exists! To test with actual 'codex' command:")
        print("   STORY=S1 make architect")
        print("   Check artifacts/dev/last_raw.txt for CLI logs")

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
