#!/usr/bin/env python3
"""
Multi-Skill Builder
Automatically splits large documentation into multiple focused skills (max 15 APIs each)

Usage:
    python3 -m skill_seekers.cli.multi_skill_builder --name sap-cdc-user-management --max-apis 15
"""

import os
import json
import re
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class MultiSkillBuilder:
    """Build multiple focused skills from scraped data."""

    def __init__(self, name: str, data_dir: str = None, output_base: str = None, max_apis: int = 15):
        """
        Initialize multi-skill builder.

        Args:
            name: Base skill name
            data_dir: Directory with scraped data (default: output/{name}_data)
            output_base: Base output directory (default: output/)
            max_apis: Maximum APIs per skill (default: 15)
        """
        self.base_name = name
        self.data_dir = data_dir or f"output/{name}_data"
        self.output_base = output_base or "output"
        self.max_apis = max_apis

    def load_scraped_data(self) -> List[Dict[str, Any]]:
        """Load scraped page data from JSON files."""
        pages = []
        pages_dir = Path(self.data_dir) / "pages"

        if not pages_dir.exists():
            logger.error("❌ Data directory not found: %s", pages_dir)
            return []

        json_files = list(pages_dir.glob("*.json"))
        if not json_files:
            logger.error("❌ No JSON files found in: %s", pages_dir)
            return []

        logger.info("📂 Loading %d pages...", len(json_files))

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page = json.load(f)
                    if page.get('content') and len(page.get('content', '')) > 50:
                        pages.append(page)
            except Exception as e:
                logger.warning("  ⚠️  Failed to load %s: %s", json_file.name, e)

        logger.info("  ✓ Loaded %d pages with content\n", len(pages))
        return pages

    def categorize_by_namespace(self, pages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize pages by API namespace.

        Examples:
        - accounts.auth.* -> authentication
        - accounts.b2b.* -> b2b
