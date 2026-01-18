#!/usr/bin/env python3
"""
Simple Skill Builder
Builds clean, organized skills from scraped data using SKILL_TEMPLATE_SIMPLE.md

Usage:
    python3 -m skill_seekers.cli.simple_skill_builder --name sap-cdc-user-management
    python3 -m skill_seekers.cli.simple_skill_builder --data-dir output/my-skill_data
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


class SimpleSkillBuilder:
    """Build skills using simple template format."""

    def __init__(self, name: str, data_dir: str = None, skill_dir: str = None):
        """
        Initialize skill builder.

        Args:
            name: Skill name
            data_dir: Directory with scraped data (default: output/{name}_data)
            skill_dir: Output directory for skill (default: output/{name})
        """
        self.name = name
        self.data_dir = data_dir or f"output/{name}_data"
        self.skill_dir = skill_dir or f"output/{name}"

        # Ensure directories exist
        os.makedirs(f"{self.skill_dir}/docs", exist_ok=True)
        os.makedirs(f"{self.skill_dir}/scripts", exist_ok=True)
        os.makedirs(f"{self.skill_dir}/assets", exist_ok=True)

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
                    # Only include pages with meaningful content
                    if page.get('content') and len(page.get('content', '')) > 50:
                        pages.append(page)
            except Exception as e:
                logger.warning("  ⚠️  Failed to load %s: %s", json_file.name, e)

        logger.info("  ✓ Loaded %d pages with content\n", len(pages))
        return pages

    def categorize_pages(self, pages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize pages by topic using API namespace patterns.

        Strategy:
        1. Detect API namespace patterns (e.g., accounts.auth.*, accounts.b2b.*)
        2. Group by namespace
        3. Fall back to keyword extraction for non-API pages
        """
        logger.info("📋 Categorizing pages...")

        categories = defaultdict(list)

        for page in pages:
            title = page.get('title', '')

            # Try to categorize by API namespace pattern
            category = self._categorize_by_api_pattern(title)

            if category:
                categories[category].append(page)
            else:
                # Fall back to keyword extraction
                keywords = self._extract_keywords(title)
                if keywords:
                    # Use first keyword as category
                    category = self._make_safe_filename(keywords[0])
                    categories[category].append(page)
                else:
                    categories['other'].append(page)

        # Convert to regular dict and filter small categories
        final_categories = {}
        other_pages = []

        for cat, cat_pages in categories.items():
            if len(cat_pages) >= 3:
                final_categories[cat] = cat_pages
            else:
                # Merge small categories into 'other'
                other_pages.extend(cat_pages)

        if other_pages:
            final_categories['other'] = other_pages

        logger.info("  ✓ Created %d categories\n", len(final_categories))

        # Log category summary
        for cat, cat_pages in sorted(final_categories.items(), key=lambda x: len(x[1]), reverse=True):
            logger.info("    - %s: %d pages", cat, len(cat_pages))

        return final_categories

    def _categorize_by_api_pattern(self, title: str) -> Optional[str]:
        """
        Categorize by API namespace pattern.

        Examples:
        - accounts.auth.* -> authentication
        - accounts.b2b.* -> b2b
        - accounts.groups.* -> groups
        - accounts.communication* -> communication
        """
        title_lower = title.lower()

        # API namespace patterns
        patterns = {
            'authentication': ['accounts.auth.', 'auth ', 'login', 'otp', 'magiclink', 'push'],
            'b2b': ['accounts.b2b.', 'b2b ', 'organization', 'business entity'],
            'groups': ['accounts.groups.', 'group '],
            'communication': ['accounts.communication', 'communication'],
            'devices': ['accounts.devices.', 'device '],
            'extensions': ['accounts.extensions.', 'extension'],
            'profile': ['profile rest', 'accounts.getprofile', 'accounts.setprofile'],
            'schema': ['schema', 'accounts.getschema', 'accounts.setschema'],
            'policies': ['policies', 'accounts.getpolicies', 'accounts.setpolicies'],
            'consent': ['consent', 'legal statement'],
            'screen-sets': ['screenset', 'screen-set'],
            'email-accounts': ['email account'],
        }

        for category, keywords in patterns.items():
            if any(keyword in title_lower for keyword in keywords):
                return category

        return None

    def _extract_keywords(self, title: str) -> List[str]:
        """Extract meaningful keywords from title."""
        # Common words to skip
        skip_words = {
            'rest', 'api', 'apis', 'the', 'and', 'with', 'for', 'from',
            'this', 'that', 'using', 'how', 'what', 'when', 'where'
        }

        # Extract capitalized words and phrases
        keywords = []

        # Pattern 1: Multi-word capitalized phrases (e.g., "User Management")
        phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', title)
        for phrase in phrases:
            clean = phrase.lower().strip()
            if clean not in skip_words:
                keywords.append(clean)

        # Pattern 2: Single capitalized words
        words = re.findall(r'\b[A-Z][a-z]{2,}\b', title)
        for word in words:
            clean = word.lower().strip()
            if clean not in skip_words and len(clean) > 3:
                keywords.append(clean)

        return keywords

    def _make_safe_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        # Replace spaces with hyphens
        safe = text.lower().replace(' ', '-')
        # Remove special characters
        safe = re.sub(r'[^\w\-]', '', safe)
        # Remove multiple hyphens
        safe = re.sub(r'-+', '-', safe)
        return safe.strip('-')

    def create_doc_files(self, categories: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Create documentation files for each category."""
        logger.info("📝 Creating documentation files...\n")

        doc_files = []

        for category, pages in categories.items():
            if not pages:
                continue

            filename = f"{category}.md"
            filepath = os.path.join(self.skill_dir, "docs", filename)

            # Build content
            lines = []
            lines.append(f"# {category.replace('-', ' ').title()}\n")
            lines.append(f"**{len(pages)} pages**\n")
            lines.append("---\n")

            for page in pages:
                # Page title
                lines.append(f"## {page['title']}\n")

                # URL reference
                lines.append(f"**Source:** `{page['url']}`\n")

                # Table of contents from headings
                if page.get('headings'):
                    lines.append("**Contents:**\n")
                    for h in page['headings'][:10]:
                        level = int(h['level'][1]) if len(h['level']) > 1 else 1
                        indent = "  " * max(0, level - 2)
                        lines.append(f"{indent}- {h['text']}")
                    lines.append("")

                # Content
                if page.get('content'):
                    lines.append(page['content'])
                    lines.append("")

                # Code examples
                if page.get('code_samples'):
                    lines.append("**Code Examples:**\n")
                    for i, sample in enumerate(page['code_samples'][:5], 1):
                        lang = sample.get('language', 'unknown')
                        code = sample.get('code', '')
                        if code:
                            lines.append(f"```{lang}")
                            lines.append(code)
                            lines.append("```\n")

                lines.append("---\n")

            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            doc_files.append(filename)
            logger.info("  ✓ %s (%d pages)", filename, len(pages))

        logger.info("")
        return doc_files

    def create_index(self, categories: Dict[str, List[Dict[str, Any]]]) -> None:
        """Create index.md navigation file."""
        lines = []
        lines.append(f"# {self.name.replace('-', ' ').title()} Documentation\n")
        lines.append("## Categories\n")

        for category, pages in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            title = category.replace('-', ' ').title()
            lines.append(f"### {title}")
            lines.append(f"- **File:** `{category}.md`")
            lines.append(f"- **Pages:** {len(pages)}\n")

        filepath = os.path.join(self.skill_dir, "docs", "index.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info("  ✓ index.md\n")

    def generate_skill_md(self, doc_files: List[str]) -> None:
        """Generate SKILL.md using simple template."""
        logger.info("📄 Generating SKILL.md...\n")

        # Load summary for description
        summary_path = os.path.join(self.data_dir, "summary.json")
        description = f"Use when working with {self.name}"

        if os.path.exists(summary_path):
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
                    # Try to infer better description from page titles
                    if summary.get('pages'):
                        description = self._infer_description(summary['pages'])
            except Exception as e:
                logger.warning("  ⚠️  Could not load summary: %s", e)

        # Format doc files list
        doc_files_list = '\n'.join([f"- **{f}** - {f.replace('-', ' ').replace('.md', '').title()}"
                                     for f in sorted(doc_files)])

        # Generate SKILL.md content
        title = self.name.replace('-', ' ').title()

        content = f"""---
name: {self.name}
description: {description}
---

# {title} Skill

{description}

## When to Use This Skill

This skill should be triggered when:
- Working with {self.name} APIs or features
- Implementing {self.name} solutions
- Debugging {self.name} code
- Integrating {self.name} into projects

## Documentation

Comprehensive documentation is available in `docs/`:

{doc_files_list}

## Quick Reference

Common patterns and examples will be added here as you use the skill.

## Resources

- **docs/** - Detailed documentation with code examples
- **scripts/** - Helper scripts for common tasks
- **assets/** - Templates and example projects
"""

        # Write SKILL.md
        filepath = os.path.join(self.skill_dir, "SKILL.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("  ✓ SKILL.md created\n")

    def _infer_description(self, pages: List[Dict[str, str]]) -> str:
        """Infer description from page titles."""
        # Extract common keywords
        keywords = []
        for page in pages[:20]:  # First 20 pages
            title = page.get('title', '')
            keywords.extend(self._extract_keywords(title))

        # Count frequency
        from collections import Counter
        keyword_counts = Counter(keywords)
        top_keywords = [k for k, _ in keyword_counts.most_common(5)]

        if top_keywords:
            keywords_str = ', '.join(top_keywords)
            return f"Use when working with {keywords_str}, or {self.name} integration"

        return f"Use when working with {self.name}"

    def build(self) -> bool:
        """Build the skill from scraped data."""
        logger.info("=" * 60)
        logger.info(f"BUILDING SKILL: {self.name}")
        logger.info("=" * 60 + "\n")

        # Load data
        pages = self.load_scraped_data()
        if not pages:
            logger.error("❌ No pages to build skill from")
            return False

        # Categorize
        categories = self.categorize_pages(pages)
        if not categories:
            logger.error("❌ Failed to categorize pages")
            return False

        # Create doc files
        doc_files = self.create_doc_files(categories)

        # Create index
        self.create_index(categories)

        # Generate SKILL.md
        self.generate_skill_md(doc_files)

        logger.info("=" * 60)
        logger.info("✅ SKILL BUILT SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"Output: {self.skill_dir}/")
        logger.info(f"  - SKILL.md")
        logger.info(f"  - docs/ ({len(doc_files)} files)")
        logger.info(f"  - scripts/")
        logger.info(f"  - assets/")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build skill from scraped data using simple template'
    )

    parser.add_argument('--name', required=True,
                       help='Skill name')
    parser.add_argument('--data-dir', type=str,
                       help='Data directory (default: output/{name}_data)')
    parser.add_argument('--skill-dir', type=str,
                       help='Output directory (default: output/{name})')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(message)s',
        force=True
    )

    # Build skill
    builder = SimpleSkillBuilder(
        name=args.name,
        data_dir=args.data_dir,
        skill_dir=args.skill_dir
    )

    success = builder.build()

    if not success:
        exit(1)


if __name__ == "__main__":
    main()
