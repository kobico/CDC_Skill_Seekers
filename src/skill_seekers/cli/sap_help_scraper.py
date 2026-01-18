#!/usr/bin/env python3
"""
SAP Help Portal Scraper
Scrapes documentation from SAP Help Portal using their JSON API.

The SAP Help Portal uses client-side rendering, but provides a JSON API
that returns the full table of contents and page content.

API Pattern:
https://help.sap.com/http.svc/pagecontent?deliverableInfo=1&deliverable_id={id}&buildNo={build}&file_path={page}.html

Usage:
    skill-seekers sap-help --deliverable-id 23708722 --build-no 1365 --name sap-cdc-api
"""

import os
import sys
import json
import time
import re
import argparse
import hashlib
import logging
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup

# Configure logging
logger = logging.getLogger(__name__)

# Import AI summarizer
try:
    from .ai_summarizer import AISummarizer
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    logger.warning("AI summarizer not available")

# Import simple skill builder
try:
    from .simple_skill_builder import SimpleSkillBuilder
    BUILDER_AVAILABLE = True
except ImportError:
    BUILDER_AVAILABLE = False
    logger.warning("Simple skill builder not available")


class SAPHelpScraper:
    """Scraper for SAP Help Portal documentation using their JSON API."""

    def __init__(self, deliverable_id: str, build_no: str, name: str,
                 max_pages: int = 100, rate_limit: float = 0.5, section: str = None,
                 skill_type: str = 'detailed', use_ai: bool = False, build_skill: bool = True):
        """
        Initialize SAP Help scraper.

        Args:
            deliverable_id: SAP deliverable ID (e.g., '23708722' for CDC)
            build_no: Documentation build number (e.g., '1365')
            name: Skill name
            max_pages: Maximum pages to scrape
            rate_limit: Delay between requests in seconds
            section: Optional section name to scrape only that section (e.g., 'REST API')
            skill_type: Type of skill to create ('overview' or 'detailed')
                       - overview: Creates concise summary, filters marketing content
                       - detailed: Includes all content for comprehensive documentation
            use_ai: Use SAP AI Core for intelligent summarization (overview skills only)
            build_skill: Automatically build skill after scraping (default: True)
        """
        self.deliverable_id = deliverable_id
        self.build_no = build_no
        self.name = name
        self.max_pages = max_pages
        self.rate_limit = rate_limit
        self.section = section
        self.skill_type = skill_type
        self.use_ai = use_ai and AI_AVAILABLE
        self.build_skill = build_skill

        # Initialize AI summarizer if requested
        self.ai_summarizer = None
        if self.use_ai and skill_type == 'overview':
            try:
                self.ai_summarizer = AISummarizer()
                logger.info("🤖 AI summarization enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize AI summarizer: {e}")
                self.use_ai = False

        # API endpoint
        self.api_base = "https://help.sap.com/http.svc/pagecontent"

        # Paths
        self.data_dir = f"output/{self.name}_data"
        self.skill_dir = f"output/{self.name}"

        # State
        self.pages: List[Dict[str, Any]] = []
        self.toc: List[Dict[str, Any]] = []

        # Create directories
        os.makedirs(f"{self.data_dir}/pages", exist_ok=True)
        os.makedirs(f"{self.skill_dir}/docs", exist_ok=True)
        os.makedirs(f"{self.skill_dir}/scripts", exist_ok=True)
        os.makedirs(f"{self.skill_dir}/assets", exist_ok=True)

    def fetch_toc(self, landing_page: str = None) -> Dict[str, Any]:
        """
        Fetch table of contents from SAP Help Portal API.

        Args:
            landing_page: Landing page file path (optional, will be discovered if not provided)

        Returns:
            Dict containing deliverable info and full TOC
        """
        # If no landing page provided, try common patterns
        if not landing_page:
            # Try to fetch with a known page to get the TOC
            landing_page = '4d83300f0ac949828f9604a8abb44065.html'  # Common CDC landing page

        params = {
            'deliverableInfo': '1',
            'deliverable_id': self.deliverable_id,
            'buildNo': self.build_no,
            'file_path': landing_page
        }

        logger.info("\n🔍 Fetching table of contents from SAP Help Portal...")
        logger.info(f"   Deliverable ID: {self.deliverable_id}")
        logger.info(f"   Build: {self.build_no}\n")

        try:
            response = requests.get(self.api_base, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'OK':
                raise Exception(f"API returned status: {data.get('status')}")

            deliverable = data['data']['deliverable']
            logger.info(f"✓ Found: {deliverable['title']}")
            logger.info(f"   Language: {deliverable.get('languageCode', 'en-US')}")
            logger.info(f"   Version: {deliverable.get('version', 'N/A')}\n")

            return data['data']

        except Exception as e:
            logger.error(f"❌ Failed to fetch TOC: {e}")
            raise

    def extract_page_ids(self, toc: List[Dict[str, Any]],
                        max_depth: int = 10) -> List[Tuple[str, str]]:
        """
        Recursively extract all page IDs and titles from TOC.

        Args:
            toc: Table of contents structure
            max_depth: Maximum recursion depth

        Returns:
            List of (page_id, title) tuples
        """
        pages = []

        def recurse(items: List[Dict[str, Any]], depth: int = 0):
            if depth > max_depth:
                return

            for item in items:
                page_id = item.get('u', '')
                title = item.get('t', 'Untitled')

                if page_id:
                    pages.append((page_id, title))

                # Recurse into children
                children = item.get('c', [])
                if children:
                    recurse(children, depth + 1)

        recurse(toc)
        return pages

    def fetch_page_content(self, page_id: str) -> Optional[str]:
        """
        Fetch page content from SAP Help Portal API.

        Args:
            page_id: Page file path (e.g., '228cd8bc68dc477094b3e0e9fe108e23.html')

        Returns:
            HTML content of the page, or None if failed
        """
        params = {
            'deliverableInfo': '1',
            'deliverable_id': self.deliverable_id,
            'buildNo': self.build_no,
            'file_path': page_id
        }

        try:
            response = requests.get(self.api_base, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'OK':
                return None

            return data['data'].get('body', '')

        except Exception as e:
            logger.warning(f"  ⚠️  Failed to fetch {page_id}: {e}")
            return None

    def filter_content(self, content: str) -> str:
        """
        Filter content based on skill type.
        For overview skills, removes marketing fluff and redundant text.

        Args:
            content: Raw content text

        Returns:
            Filtered content
        """
        if self.skill_type != 'overview':
            return content

        # Patterns to remove for overview skills
        remove_patterns = [
            r'You can watch videos.*?(?:page|platform)\.',
            r'Open this video in a new window',
            r'Some videos are only accessible.*?page\.',
            r'To find out how to get.*?page\.',
            r'For more information.*?refer to.*?\.',
            r'Visit the.*?page for.*?\.',
        ]

        filtered = content
        for pattern in remove_patterns:
            filtered = re.sub(pattern, '', filtered, flags=re.DOTALL | re.IGNORECASE)

        # Remove excessive whitespace
        filtered = re.sub(r'\n{3,}', '\n\n', filtered)
        filtered = re.sub(r' {2,}', ' ', filtered)

        return filtered.strip()

    def parse_html_content(self, html: str, url: str, title: str) -> Dict[str, Any]:
        """
        Parse HTML content and extract structured data.

        Args:
            html: HTML content
            url: Page URL/ID
            title: Page title

        Returns:
            Dict with structured page data
        """
        soup = BeautifulSoup(html, 'html.parser')

        page = {
            'url': url,
            'title': title,
            'content': '',
            'headings': [],
            'code_samples': [],
            'links': []
        }

        # Extract headings
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = h.get_text().strip()
            if text:
                page['headings'].append({
                    'level': h.name,
                    'text': text,
                    'id': h.get('id', '')
                })

        # Extract code samples
        for code_elem in soup.select('pre code, pre, .code-block'):
            code = code_elem.get_text()
            if len(code.strip()) > 10:
                # Try to detect language
                lang = 'unknown'
                classes = code_elem.get('class', [])
                for cls in classes:
                    if 'language-' in cls:
                        lang = cls.replace('language-', '')
                        break

                page['code_samples'].append({
                    'code': code.strip(),
                    'language': lang
                })

        # Extract paragraphs
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 20:
                paragraphs.append(text)

        content = '\n\n'.join(paragraphs)

        # Apply content filtering based on skill type
        page['content'] = self.filter_content(content)

        return page

    def save_page(self, page: Dict[str, Any]) -> None:
        """Save page data to JSON file."""
        if not page.get('content') or len(page.get('content', '')) < 50:
            logger.debug(f"Skipping page with empty/short content: {page.get('url', 'unknown')}")
            return

        url_hash = hashlib.md5(page['url'].encode()).hexdigest()[:10]
        safe_title = re.sub(r'[^\w\s-]', '', page['title'])[:50]
        safe_title = re.sub(r'[-\s]+', '_', safe_title)

        filename = f"{safe_title}_{url_hash}.json"
        filepath = os.path.join(self.data_dir, "pages", filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page, f, indent=2, ensure_ascii=False)

    def find_section_pages(self, toc: List[Dict[str, Any]], section_name: str) -> List[Tuple[str, str]]:
        """
        Find and extract all pages from a specific section.

        Args:
            toc: Table of contents structure
            section_name: Name of the section to extract

        Returns:
            List of (page_id, title) tuples for that section
        """
        def find_and_extract(items, target_title, pages=None):
            if pages is None:
                pages = []

            for item in items:
                if item.get('t') == target_title:
                    # Found the target section, extract all pages recursively
                    def extract_all(node):
                        if node.get('u'):
                            pages.append((node['u'], node.get('t', 'Untitled')))
                        if node.get('c'):
                            for child in node['c']:
                                extract_all(child)
                    extract_all(item)
                    return pages

                # Recurse into children
                if item.get('c'):
                    result = find_and_extract(item['c'], target_title, pages)
                    if result:
                        return result

            return pages if pages else None

        return find_and_extract(toc, section_name) or []

    def scrape_all(self) -> None:
        """Scrape all pages from SAP Help Portal."""
        logger.info("=" * 60)
        logger.info(f"SCRAPING SAP HELP PORTAL: {self.name}")
        logger.info("=" * 60 + "\n")

        # Fetch TOC
        toc_data = self.fetch_toc()
        full_toc = toc_data['deliverable']['fullToc']

        # Extract page IDs (all or specific section)
        if self.section:
            logger.info(f"📋 Extracting pages from section: {self.section}...")
            page_list = self.find_section_pages(full_toc, self.section)
            if not page_list:
                logger.error(f"❌ Section '{self.section}' not found in TOC")
                return
            logger.info(f"   Found {len(page_list)} pages in '{self.section}' section\n")
        else:
            logger.info("📋 Extracting page list from TOC...")
            page_list = self.extract_page_ids(full_toc)
            logger.info(f"   Found {len(page_list)} pages in documentation\n")

        # Limit pages if needed
        if len(page_list) > self.max_pages:
            logger.info(f"⚠️  Limiting to {self.max_pages} pages (found {len(page_list)})\n")
            page_list = page_list[:self.max_pages]

        # Scrape each page
        logger.info(f"🔄 Scraping {len(page_list)} pages...\n")

        for idx, (page_id, title) in enumerate(page_list, 1):
            logger.info(f"  [{idx}/{len(page_list)}] {title}")

            # Fetch content
            html_content = self.fetch_page_content(page_id)

            if html_content:
                # Parse and save
                page = self.parse_html_content(html_content, page_id, title)
                self.save_page(page)
                self.pages.append(page)

            # Rate limiting
            if self.rate_limit > 0:
                time.sleep(self.rate_limit)

            # Progress indicator
            if idx % 10 == 0:
                logger.info(f"  [Progress: {idx}/{len(page_list)} pages]\n")

        logger.info(f"\n✅ Scraped {len(self.pages)} pages with content")

        # Save summary
        self.save_summary()

        # Build skill automatically if enabled
        if self.build_skill and BUILDER_AVAILABLE:
            logger.info("\n" + "=" * 60)
            logger.info("BUILDING SKILL")
            logger.info("=" * 60 + "\n")

            try:
                builder = SimpleSkillBuilder(name=self.name)
                success = builder.build()

                if success:
                    logger.info("\n✅ Skill built successfully!")
                else:
                    logger.warning("\n⚠️  Skill building failed")
            except Exception as e:
                logger.error(f"\n❌ Error building skill: {e}")
                logger.info("   You can build manually with:")
                logger.info(f"   python3 -m skill_seekers.cli.simple_skill_builder --name {self.name}")

    def save_summary(self) -> None:
        """Save scraping summary."""
        summary = {
            'name': self.name,
            'deliverable_id': self.deliverable_id,
            'build_no': self.build_no,
            'total_pages': len(self.pages),
            'pages': [{'title': p['title'], 'url': p['url']} for p in self.pages]
        }

        with open(f"{self.data_dir}/summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point for SAP Help scraper."""
    parser = argparse.ArgumentParser(
        description='Scrape SAP Help Portal documentation',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--deliverable-id', required=True,
                       help='SAP deliverable ID (e.g., 23708722 for CDC)')
    parser.add_argument('--build-no', required=True,
                       help='Documentation build number (e.g., 1365)')
    parser.add_argument('--name', required=True,
                       help='Skill name (e.g., sap-cdc-api)')
    parser.add_argument('--max-pages', type=int, default=100,
                       help='Maximum pages to scrape (default: 100)')
    parser.add_argument('--rate-limit', type=float, default=0.5,
                       help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--section', type=str,
                       help='Scrape only a specific section (e.g., "REST API", "Web SDK")')
    parser.add_argument('--skill-type', type=str, default='detailed',
                       choices=['overview', 'detailed'],
                       help='Type of skill to create: "overview" (concise, filtered) or "detailed" (comprehensive). Default: detailed')
    parser.add_argument('--use-ai', action='store_true',
                       help='Use SAP AI Core for intelligent summarization (overview skills only). Requires configuration in ~/.skillseekers/ai_config.env')
    parser.add_argument('--no-build', action='store_true',
                       help='Skip automatic skill building after scraping')
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

    # Create scraper and run
    scraper = SAPHelpScraper(
        deliverable_id=args.deliverable_id,
        build_no=args.build_no,
        name=args.name,
        max_pages=args.max_pages,
        rate_limit=args.rate_limit,
        section=args.section,
        skill_type=args.skill_type,
        use_ai=args.use_ai,
        build_skill=not args.no_build
    )

    try:
        scraper.scrape_all()

        # Only show next steps if skill wasn't built automatically
        if not scraper.build_skill or not BUILDER_AVAILABLE:
            logger.info("\n" + "=" * 60)
            logger.info("NEXT STEPS")
            logger.info("=" * 60)
            logger.info(f"\n1. Build skill:")
            logger.info(f"   cd Skill_Seekers")
            logger.info(f"   python3 -m skill_seekers.cli.simple_skill_builder --name {args.name}")
            logger.info(f"\n2. Deploy:")
            logger.info(f"   ./deploy-skills-to-cdc.sh {args.name}")
        else:
            logger.info("\n" + "=" * 60)
            logger.info("NEXT STEPS")
            logger.info("=" * 60)
            logger.info(f"\n1. Review skill:")
            logger.info(f"   cat output/{args.name}/SKILL.md")
            logger.info(f"\n2. Deploy:")
            logger.info(f"   ./deploy-skills-to-cdc.sh {args.name}")

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
