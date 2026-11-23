"""Top-level CLI entry point for Composio Research Agent."""

from __future__ import annotations

import sys
from research_agent.use_cases.run_single_research import main

if __name__ == "__main__":
    sys.exit(main())
