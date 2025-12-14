#!/usr/bin/env python3
"""
MAGNET Chat CLI - Interactive design terminal

Usage:
    python scripts/chat_cli.py

Commands:
    - Natural language: "Design a 32ft patrol boat, 25 knots, 4 crew"
    - status - Show current design status
    - get <path> - Get a state value (e.g., get hull.lwl)
    - set <path> <value> - Set a value
    - help - Show available commands
    - quit/exit - Exit the CLI
"""

import sys
import os

# Ensure MAGNET is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magnet.bootstrap.app import MAGNETApp
from magnet.core.state_manager import StateManager
from magnet.kernel.conductor import Conductor
from magnet.agents.llm_client import LLMClient
from magnet.ui.chat import ChatHandler


def print_banner():
    """Print welcome banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    MAGNET Design System                      ║
║              Chat-Driven Ship Design Spiral                  ║
╠══════════════════════════════════════════════════════════════╣
║  Try: "Design a 32ft patrol boat, 25 knots, 4 crew"          ║
║  Commands: status, get <path>, set <path> <val>, help, quit  ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    """Main CLI entry point."""
    print_banner()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  Warning: ANTHROPIC_API_KEY not set")
        print("   Natural language parsing will be disabled.")
        print("   Set it with: export ANTHROPIC_API_KEY=your_key")
        print()
        llm = None
    else:
        print("✓ LLM client ready")
        llm = LLMClient()

    # Build app
    print("✓ Initializing MAGNET...")
    app = MAGNETApp().build()
    state = app.container.resolve(StateManager)
    conductor = app.container.resolve(Conductor)

    # Create chat handler
    handler = ChatHandler(state=state, conductor=conductor, llm=llm)
    print("✓ Chat handler ready")
    print()
    print("─" * 60)
    print()

    # REPL loop
    while True:
        try:
            user_input = input("MAGNET> ").strip()

            if not user_input:
                continue

            # Handle exit commands
            if user_input.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break

            # Process through chat handler
            response = handler.process_message(user_input)
            print()
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'quit' to exit.")
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print()


if __name__ == "__main__":
    main()
