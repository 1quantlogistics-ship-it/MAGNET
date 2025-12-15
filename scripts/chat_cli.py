#!/usr/bin/env python3
"""
MAGNET Chat CLI v1 - Interactive design terminal with async support

Usage:
    python scripts/chat_cli.py

Commands:
    - Natural language: "Design a 32ft patrol boat, 25 knots, 4 crew"
    - Refinements: "make it faster", "add 2 more crew"
    - phases - Show phase status tree
    - export [path] - Export design with phase report
    - status - Show current design status
    - get <path> - Get a state value (e.g., get hull.lwl)
    - set <path> <value> - Set a value
    - help - Show available commands
    - quit/exit - Exit the CLI
"""

import sys
import os
import asyncio

# Ensure MAGNET is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from magnet.bootstrap.app import MAGNETApp
from magnet.core.state_manager import StateManager
from magnet.kernel.conductor import Conductor
from magnet.agents.llm_client import LLMClient
from magnet.ui.chat import ChatHandler
from magnet.glue.lifecycle.exporter import DesignExporter


def print_banner():
    """Print welcome banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    MAGNET Design System                      ║
║              Chat-Driven Ship Design Spiral                  ║
║                        CLI v1.0                              ║
╠══════════════════════════════════════════════════════════════╣
║  Try: "Design a 32ft patrol boat, 25 knots, 4 crew"          ║
║  Refine: "make it faster", "add 2 more crew"                 ║
║  Commands: phases, export, status, get <path>, help, quit    ║
╚══════════════════════════════════════════════════════════════╝
""")


async def main():
    """Main async CLI entry point."""
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
    print("✓ Chat handler ready (async mode)")
    print()
    print("─" * 60)
    print()

    # Get running loop for input handling (CLI v1 Fix #12)
    loop = asyncio.get_running_loop()

    # Async REPL loop
    while True:
        try:
            # Use run_in_executor for blocking input (cross-version safe)
            user_input = await loop.run_in_executor(None, lambda: input("MAGNET> "))
            user_input = user_input.strip()

            if not user_input:
                continue

            # Handle exit commands
            if user_input.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break

            # Handle CLI-specific commands
            if user_input.lower() == "phases":
                print()
                print(_render_phases(state))
                print()
                continue

            if user_input.lower().startswith("export"):
                print()
                print(_handle_export(user_input, state, handler))
                print()
                continue

            # Process through async chat handler
            response = await handler.process_message_async(user_input)
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


def _render_phases(state: StateManager) -> str:
    """Render phase status using PhaseNavigator or fallback."""
    try:
        from magnet.ui.phase_navigator import PhaseNavigator
        navigator = PhaseNavigator(state)
        return navigator.render_ascii()
    except ImportError:
        # Fallback if PhaseNavigator not available
        lines = ["**Phase Status:**"]
        phases = ["mission", "hull", "structure", "propulsion", "weight", "stability"]
        icons = {"pending": "○", "completed": "●", "error": "✗", "active": "◉"}

        for phase in phases:
            status = state.get(f"phase_states.{phase}.status") or "pending"
            icon = icons.get(status, "?")
            lines.append(f"  {icon} {phase}: {status}")

        return "\n".join(lines)


def _handle_export(user_input: str, state: StateManager, handler: ChatHandler) -> str:
    """Handle export command using DesignExporter (CLI v1: kernel owns export logic)."""
    parts = user_input.split(maxsplit=1)
    path = parts[1] if len(parts) > 1 else "design_export.json"

    try:
        # CLI v1: Use DesignExporter with phase report
        exporter = DesignExporter(state)

        # Get session from conductor for phase results
        session = handler.conductor.get_session() if handler.conductor else None

        # Export with phase report (kernel-owned serialization)
        export_json = exporter.export_with_phase_report(session=session)

        with open(path, 'w') as f:
            f.write(export_json)

        # Count completed phases for summary
        completed = 0
        total = 0
        if session and hasattr(session, 'phase_results'):
            total = len(session.phase_results)
            completed = len(getattr(session, 'completed_phases', []))

        return (
            f"✓ Exported to {path}\n"
            f"  Phases: {completed}/{total} completed"
        )
    except Exception as e:
        return f"✗ Export failed: {e}"


if __name__ == "__main__":
    asyncio.run(main())
