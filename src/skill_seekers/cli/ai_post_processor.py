#!/usr/bin/env python3
"""
AI Post-Processor for Skills
Applies AI summarization to already-built skills to create concise overview versions.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_seekers.cli.ai_summarizer import AISummarizer

logger = logging.getLogger(__name__)


class AIPostProcessor:
    """Post-processes built skills with AI summarization."""

    def __init__(self, skill_dir: str, use_ai: bool = True):
        """
        Initialize post-processor.

        Args:
            skill_dir: Path to built skill directory (e.g., output/sap-cdc-rest-api-overview)
            use_ai: Whether to use AI summarization (falls back to rule-based if False)
        """
        self.skill_dir = Path(skill_dir)
        self.use_ai = use_ai

        # Initialize AI summarizer
        self.ai_summarizer = None
        if use_ai:
            try:
                self.ai_summarizer = AISummarizer()
                if self.ai_summarizer._is_configured():
                    logger.info("🤖 AI summarization enabled")
                else:
                    logger.warning("⚠️  AI not configured, will use rule-based summarization")
                    self.use_ai = False
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize AI: {e}")
                self.use_ai = False

    def load_pages_from_data(self) -> List[Dict[str, Any]]:
        """Load pages from the skill's data directory."""
        # Try to find data directory
        skill_name = self.skill_dir.name
        data_dir = self.skill_dir.parent / f"{skill_name}_data" / "pages"

        if not data_dir.exists():
            logger.error(f"❌ Data directory not found: {data_dir}")
            logger.error("   Make sure the skill was built with scraped data")
            return []

        pages = []
        for json_file in data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    pages.append(json.load(f))
            except Exception as e:
                logger.warning(f"⚠️  Failed to load {json_file}: {e}")

        return pages

    def summarize_reference_file(self, ref_file: Path, pages: List[Dict[str, Any]]) -> str:
        """
        Summarize a reference file using AI.

        Args:
            ref_file: Path to reference markdown file
            pages: List of page data for context

        Returns:
            Summarized content
        """
        if not ref_file.exists():
            return ""

        # Read current content
        with open(ref_file, 'r', encoding='utf-8') as f:
            current_content = f.read()

        # If using AI and it's configured
        if self.use_ai and self.ai_summarizer:
            logger.info(f"  🤖 Summarizing with AI: {ref_file.name}")

            try:
                # Use AI to summarize
                summary = self.ai_summarizer.summarize_pages(
                    pages,
                    skill_name=self.skill_dir.name,
                    max_length=5000
                )

                return summary

            except Exception as e:
                logger.warning(f"  ⚠️  AI summarization failed: {e}")
                logger.info("  📝 Using rule-based fallback")

        # Rule-based summarization (fallback)
        return self._rule_based_summarize(current_content, pages)

    def _rule_based_summarize(self, content: str, pages: List[Dict[str, Any]]) -> str:
        """
        Rule-based summarization as fallback.

        Extracts:
        - First paragraph from each section
        - Key headings
        - Essential code examples (shortened)
        """
        lines = content.split('\n')
        summary_lines = []

        current_section = None
        in_code_block = False
        code_line_count = 0
        max_code_lines = 10  # Limit code examples

        for line in lines:
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    code_line_count = 0
                summary_lines.append(line)
                continue

            # In code block - limit lines
            if in_code_block:
                code_line_count += 1
                if code_line_count <= max_code_lines:
                    summary_lines.append(line)
                elif code_line_count == max_code_lines + 1:
                    summary_lines.append("... (truncated)")
                continue

            # Keep headers
            if line.startswith('#'):
                current_section = line
                summary_lines.append(line)
                continue

            # Keep first paragraph of each section (non-empty lines)
            if line.strip() and current_section:
                # Add first meaningful line after header
                if len(line.strip()) > 20:  # Skip very short lines
                    summary_lines.append(line)
                    current_section = None  # Only first paragraph
                continue

        return '\n'.join(summary_lines)

    def generate_skill_description(self, pages: List[Dict[str, Any]]) -> str:
        """
        Generate skill description using AI or rule-based approach.

        Args:
            pages: List of page data

        Returns:
            Generated description string
        """
        if self.use_ai and self.ai_summarizer:
            logger.info("  🤖 Generating description with AI...")

            try:
                # Prepare content for AI
                titles = [p.get('title', '') for p in pages[:5]]
                titles_text = '\n'.join(f"- {t}" for t in titles if t)

                prompt = f"""Based on these documentation page titles, create a concise skill description in the format "Use when working with X, Y, Z, or [skill-name] integration."

Page titles:
{titles_text}

Requirements:
- Extract 5-8 key technical terms/concepts
- Focus on technologies, APIs, protocols, authentication methods
- Format: "Use when working with [term1], [term2], [term3], or {self.skill_dir.name} integration"
- Keep it under 150 characters
- Be specific and technical

Output ONLY the description, nothing else."""

                # Call AI
                description = self.ai_summarizer._call_ai_core(
                    prompt,
                    self.ai_summarizer._get_access_token()
                )

                # Clean up response
                description = description.strip().strip('"').strip("'")
                logger.info(f"  ✓ Generated: {description}")
                return description

            except Exception as e:
                logger.warning(f"  ⚠️  AI description generation failed: {e}")
                logger.info("  📝 Using rule-based fallback")

        # Rule-based fallback
        return self._generate_description_rule_based(pages)

    def _generate_description_rule_based(self, pages: List[Dict[str, Any]]) -> str:
        """Generate description using rule-based extraction."""
        from collections import Counter
        import re

        key_terms = []
        common_words = {'the', 'and', 'with', 'for', 'from', 'this', 'that', 'using', 'instructional', 'video', 'example', 'code', 'method'}

        for page in pages[:5]:
            title = page.get('title', '')
            if title:
                words = re.findall(r'\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\b', title)
                for word in words:
                    if word.lower() not in common_words and len(word) > 2:
                        key_terms.append(word)

        term_counts = Counter(key_terms)
        most_common = [term for term, count in term_counts.most_common(10)]

        if most_common:
            # Group related terms for more natural description
            # Simplify long phrases
            simplified = []
            for term in most_common[:6]:  # Limit to 6 most relevant
                # Shorten "SAP Customer Data Cloud" to "CDC"
                if 'SAP Customer Data Cloud' in term:
                    if 'CDC' not in simplified:
                        simplified.append('CDC')
                # Keep other terms
                elif term not in simplified:
                    simplified.append(term)

            terms_str = ', '.join(simplified)
            return f'Use when working with {terms_str}, or {self.skill_dir.name} integration'

        return f'Use when working with {self.skill_dir.name}'

    def update_skill_description(self, description: str) -> bool:
        """
        Update SKILL.md with new description.

        Args:
            description: New description to use

        Returns:
            True if successful
        """
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            return False

        try:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update description in frontmatter
            import re
            content = re.sub(
                r'description: .*',
                f'description: {description}',
                content,
                count=1
            )

            # Update description in body
            content = re.sub(
                r'Use when working with .*?, generated from',
                f'{description}, generated from',
                content,
                count=1
            )

            with open(skill_md, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to update SKILL.md: {e}")
            return False

    def process_skill(self) -> bool:
        """
        Process the skill with AI summarization.

        Returns:
            True if successful, False otherwise
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"AI POST-PROCESSING: {self.skill_dir.name}")
        logger.info("=" * 60 + "\n")

        # Check if skill directory exists
        if not self.skill_dir.exists():
            logger.error(f"❌ Skill directory not found: {self.skill_dir}")
            return False

        # Load pages from data directory
        logger.info("📂 Loading scraped data...")
        pages = self.load_pages_from_data()

        if not pages:
            logger.error("❌ No pages found - cannot summarize")
            return False

        logger.info(f"  ✓ Loaded {len(pages)} pages\n")

        # Generate and update description
        logger.info("📝 Generating skill description...")
        description = self.generate_skill_description(pages)
        if self.update_skill_description(description):
            logger.info(f"  ✓ Updated SKILL.md description\n")

        # Process reference files
        docs_dir = self.skill_dir / "docs"
        if not docs_dir.exists():
            logger.error(f"❌ Docs directory not found: {docs_dir}")
            return False

        logger.info("📝 Processing reference files...")

        # Process other.md (main reference file)
        other_md = docs_dir / "other.md"
        if other_md.exists():
            summary = self.summarize_reference_file(other_md, pages)

            if summary:
                # Backup original
                backup_path = docs_dir / "other.md.backup"
                if not backup_path.exists():
                    with open(other_md, 'r', encoding='utf-8') as f:
                        original = f.read()
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(original)
                    logger.info(f"  💾 Backed up original to: {backup_path.name}")

                # Write summarized version
                with open(other_md, 'w', encoding='utf-8') as f:
                    f.write(summary)

                # Show size comparison
                original_size = backup_path.stat().st_size if backup_path.exists() else 0
                new_size = other_md.stat().st_size
                reduction = ((original_size - new_size) / original_size * 100) if original_size > 0 else 0

                logger.info(f"  ✓ Summarized other.md")
                logger.info(f"    Original: {original_size:,} bytes")
                logger.info(f"    New: {new_size:,} bytes")
                logger.info(f"    Reduction: {reduction:.1f}%")

        logger.info("\n✅ Post-processing complete!")
        logger.info(f"   Skill: {self.skill_dir}")
        logger.info(f"   Description: {description}")
        logger.info(f"   Backup: {self.skill_dir}/docs/other.md.backup")

        return True


def main():
    """Main entry point for AI post-processor."""
    parser = argparse.ArgumentParser(
        description='Apply AI summarization to built skills',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Summarize with AI
  python3 -m skill_seekers.cli.ai_post_processor output/sap-cdc-rest-api-overview

  # Use rule-based only (no AI)
  python3 -m skill_seekers.cli.ai_post_processor output/sap-cdc-rest-api-overview --no-ai

  # Verbose output
  python3 -m skill_seekers.cli.ai_post_processor output/sap-cdc-rest-api-overview -v
        """
    )

    parser.add_argument('skill_dir', type=str,
                       help='Path to built skill directory (e.g., output/sap-cdc-rest-api-overview)')
    parser.add_argument('--no-ai', action='store_true',
                       help='Use rule-based summarization only (no AI)')
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

    # Create processor
    processor = AIPostProcessor(
        skill_dir=args.skill_dir,
        use_ai=not args.no_ai
    )

    # Process skill
    try:
        success = processor.process_skill()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
