#!/usr/bin/env python3
"""TATLAM Batch Scenario Generator - Minimal Entrypoint.

This script serves as the entry point for batch scenario generation.
All CLI logic is handled by tatlam.cli.batch_cmd.

Phase 2 Refactoring: Reduced from 896 lines to 8 lines.
"""
from tatlam.cli.batch_cmd import main

if __name__ == "__main__":
    main()
