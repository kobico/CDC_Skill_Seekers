#!/usr/bin/env python3
"""
Skill Enhancer - Final polish for generated skills
Splits documentation, adds scripts, templates, and patterns
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class SkillEnhancer:
    """Enhances generated skills with focused docs, scripts, and templates."""

    def __init__(self, skill_dir: str):
        """
        Initialize enhancer.

        Args:
            skill_dir: Path to skill directory (e.g., output/cdc-api-writer)
        """
        self.skill_dir = Path(skill_dir)
        self.skill_name = self.skill_dir.name
        self.docs_dir = self.skill_dir / "docs"
        self.scripts_dir = self.skill_dir / "scripts"
        self.assets_dir = self.skill_dir / "assets"

    def split_documentation(self) -> Dict[str, str]:
        """
        Split docs/other.md into focused topic files.

        Returns:
            Dict mapping topic names to file paths
        """
        other_md = self.docs_dir / "other.md"
        if not other_md.exists():
            logger.warning("No other.md found to split")
            return {}

        with open(other_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Detect topics based on headings
        topics = self._detect_topics(content)

        if not topics:
            logger.info("No clear topics detected, keeping single file")
            return {}

        # Split content by topics
        split_files = {}
        for topic_name, topic_content in topics.items():
            filename = f"{topic_name}.md"
            filepath = self.docs_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(topic_content)

            split_files[topic_name] = str(filepath)
            logger.info(f"  ✓ Created {filename}")

        # Keep original as backup
        backup_path = self.docs_dir / "other.md.original"
        other_md.rename(backup_path)
        logger.info(f"  💾 Backed up original to other.md.original")

        return split_files

    def _detect_topics(self, content: str) -> Dict[str, str]:
        """Detect and split content by topics."""
        topics = {}

        # Common topic patterns
        topic_patterns = {
            'authentication': ['authentication', 'oauth', 'jwt', 'token', 'signing', 'keys'],
            'rest-apis': ['rest api', 'endpoint', 'request', 'response', 'http'],
            'error-handling': ['error', 'exception', 'validation', 'troubleshooting'],
            'integration': ['integration', 'setup', 'configuration', 'getting started'],
        }

        # Split by h2 headings
        sections = re.split(r'\n## ', content)

        # Group sections by topic
        for topic_key, keywords in topic_patterns.items():
            topic_sections = []

            for section in sections:
                section_lower = section.lower()
                if any(keyword in section_lower for keyword in keywords):
                    topic_sections.append('## ' + section if not section.startswith('#') else section)

            if topic_sections:
                topics[topic_key] = '\n\n'.join(topic_sections)

        return topics

    def generate_scripts(self) -> List[str]:
        """
        Generate useful scripts for common tasks.

        Returns:
            List of generated script paths
        """
        scripts = []

        # Script 1: API Test Script
        test_script = self.scripts_dir / "test-api.sh"
        test_content = """#!/bin/bash
# Test CDC API Connection
# Usage: ./test-api.sh <api-key> <api-secret>

API_KEY="${1:-YOUR_API_KEY}"
API_SECRET="${2:-YOUR_API_SECRET}"
BASE_URL="https://accounts.gigya.com"

echo "Testing CDC API connection..."
echo "API Key: $API_KEY"

# Test accounts.getAccountInfo
curl -X POST "$BASE_URL/accounts.getAccountInfo" \\
  -d "apiKey=$API_KEY" \\
  -d "secret=$API_SECRET" \\
  -d "UID=test-user-id"

echo ""
echo "✓ Test complete"
"""
        with open(test_script, 'w', encoding='utf-8') as f:
            f.write(test_content)
        test_script.chmod(0o755)
        scripts.append(str(test_script))
        logger.info(f"  ✓ Created test-api.sh")

        # Script 2: Generate JWT Token
        jwt_script = self.scripts_dir / "generate-jwt.py"
        jwt_content = """#!/usr/bin/env python3
\"\"\"
Generate JWT token for CDC API authentication
Usage: python3 generate-jwt.py <private-key-file> <api-key>
\"\"\"

import sys
import time
import jwt

def generate_jwt_token(private_key_path, api_key):
    with open(private_key_path, 'r') as f:
        private_key = f.read()

    payload = {
        'apiKey': api_key,
        'iat': int(time.time()),
        'exp': int(time.time()) + 3600  # 1 hour expiration
    }

    token = jwt.encode(payload, private_key, algorithm='RS256')
    return token

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 generate-jwt.py <private-key-file> <api-key>")
        sys.exit(1)

    token = generate_jwt_token(sys.argv[1], sys.argv[2])
    print(f"JWT Token: {token}")
"""
        with open(jwt_script, 'w', encoding='utf-8') as f:
            f.write(jwt_content)
        jwt_script.chmod(0o755)
        scripts.append(str(jwt_script))
        logger.info(f"  ✓ Created generate-jwt.py")

        return scripts

    def create_templates(self) -> List[str]:
        """
        Create example templates in assets/.

        Returns:
            List of created template paths
        """
        templates = []

        # Template 1: API Request Template
        request_template = self.assets_dir / "api-request-template.json"
        request_content = {
            "apiKey": "YOUR_API_KEY",
            "secret": "YOUR_SECRET",
            "UID": "user-id",
            "profile": {
                "firstName": "John",
                "lastName": "Doe",
                "email": "john.doe@example.com"
            }
        }
        with open(request_template, 'w', encoding='utf-8') as f:
            json.dump(request_content, f, indent=2)
        templates.append(str(request_template))
        logger.info(f"  ✓ Created api-request-template.json")

        # Template 2: Configuration Template
        config_template = self.assets_dir / "config-template.json"
        config_content = {
            "apiKey": "YOUR_API_KEY",
            "dataCenter": "us1.gigya.com",
            "userKey": "YOUR_USER_KEY",
            "secret": "YOUR_SECRET",
            "timeout": 30000,
            "retries": 3
        }
        with open(config_template, 'w', encoding='utf-8') as f:
            json.dump(config_content, f, indent=2)
        templates.append(str(config_template))
        logger.info(f"  ✓ Created config-template.json")

        # Template 3: Example Integration
        integration_template = self.assets_dir / "example-integration.js"
        integration_content = """// Example CDC API Integration
const axios = require('axios');

class CDCClient {
  constructor(apiKey, secret, dataCenter = 'us1.gigya.com') {
    this.apiKey = apiKey;
    this.secret = secret;
    this.baseUrl = `https://accounts.${dataCenter}`;
  }

  async getAccountInfo(uid) {
    const response = await axios.post(`${this.baseUrl}/accounts.getAccountInfo`, {
      apiKey: this.apiKey,
      secret: this.secret,
      UID: uid
    });
    return response.data;
  }

  async setAccountInfo(uid, profile) {
    const response = await axios.post(`${this.baseUrl}/accounts.setAccountInfo`, {
      apiKey: this.apiKey,
      secret: this.secret,
      UID: uid,
      profile: JSON.stringify(profile)
    });
    return response.data;
  }
}

// Usage example
const client = new CDCClient('YOUR_API_KEY', 'YOUR_SECRET');
client.getAccountInfo('user-123')
  .then(data => console.log('Account:', data))
  .catch(err => console.error('Error:', err));
"""
        with open(integration_template, 'w', encoding='utf-8') as f:
            f.write(integration_content)
        templates.append(str(integration_template))
        logger.info(f"  ✓ Created example-integration.js")

        return templates

    def extract_patterns(self) -> List[Dict[str, str]]:
        """
        Extract common patterns from documentation.

        Returns:
            List of pattern dicts with 'title' and 'code'
        """
        patterns = []

        # Load scraped data to extract code samples
        data_dir = self.skill_dir.parent / f"{self.skill_name}_data" / "pages"
        if not data_dir.exists():
            logger.warning("No scraped data found for pattern extraction")
            return patterns

        # Collect code samples
        code_samples = []
        for json_file in data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    page = json.load(f)
                    code_samples.extend(page.get('code_samples', []))
            except Exception as e:
                logger.debug(f"Error loading {json_file}: {e}")

        # Extract unique, useful patterns
        seen_codes = set()
        for sample in code_samples[:20]:  # Limit to first 20
            code = sample.get('code', '')
            lang = sample.get('language', 'unknown')

            if len(code) > 50 and len(code) < 500 and code not in seen_codes:
                patterns.append({
                    'title': f'{lang.title()} Example',
                    'code': code,
                    'language': lang
                })
                seen_codes.add(code)

                if len(patterns) >= 5:  # Limit to 5 patterns
                    break

        return patterns

    def update_skill_md(self, split_files: Dict[str, str], patterns: List[Dict[str, str]]) -> None:
        """Update SKILL.md with new documentation structure and patterns."""
        skill_md = self.skill_dir / "SKILL.md"
        if not skill_md.exists():
            logger.warning("SKILL.md not found")
            return

        with open(skill_md, 'r', encoding='utf-8') as f:
            content = f.read()

        # Update documentation section
        if split_files:
            doc_list = []
            for topic in sorted(split_files.keys()):
                doc_list.append(f"- **[{topic}.md](docs/{topic}.md)** - {topic.replace('-', ' ').title()}")

            doc_section = "## Documentation\n\nComprehensive documentation is available in `docs/`:\n\n" + '\n'.join(doc_list)

            # Replace documentation section
            content = re.sub(
                r'## Documentation.*?(?=\n## )',
                doc_section + '\n\n',
                content,
                flags=re.DOTALL
            )

        # Update Quick Reference with patterns
        if patterns:
            patterns_md = "## Quick Reference\n\n### Common Patterns\n\n"
            for i, pattern in enumerate(patterns, 1):
                patterns_md += f"**{pattern['title']}**:\n```{pattern['language']}\n{pattern['code']}\n```\n\n"

            # Replace Quick Reference section
            content = re.sub(
                r'## Quick Reference.*?(?=\n## )',
                patterns_md,
                content,
                flags=re.DOTALL
            )

        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("  ✓ Updated SKILL.md")

    def enhance(self) -> bool:
        """
        Run all enhancements.

        Returns:
            True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info(f"ENHANCING SKILL: {self.skill_name}")
        logger.info("=" * 60 + "\n")

        # 1. Split documentation
        logger.info("📄 Splitting documentation into focused topics...")
        split_files = self.split_documentation()
        if split_files:
            logger.info(f"  ✓ Created {len(split_files)} topic files\n")
        else:
            logger.info("  ℹ️  Keeping single documentation file\n")

        # 2. Generate scripts
        logger.info("📝 Generating utility scripts...")
        scripts = self.generate_scripts()
        logger.info(f"  ✓ Created {len(scripts)} scripts\n")

        # 3. Create templates
        logger.info("📋 Creating example templates...")
        templates = self.create_templates()
        logger.info(f"  ✓ Created {len(templates)} templates\n")

        # 4. Extract patterns
        logger.info("🔍 Extracting common patterns...")
        patterns = self.extract_patterns()
        logger.info(f"  ✓ Extracted {len(patterns)} patterns\n")

        # 5. Update SKILL.md
        logger.info("📝 Updating SKILL.md...")
        self.update_skill_md(split_files, patterns)
        logger.info("")

        logger.info("✅ Enhancement complete!")
        logger.info(f"   Skill: {self.skill_dir}")
        logger.info(f"   Documentation: {len(split_files)} topic files")
        logger.info(f"   Scripts: {len(scripts)} utility scripts")
        logger.info(f"   Templates: {len(templates)} examples")
        logger.info(f"   Patterns: {len(patterns)} code patterns")

        return True


def main():
    """Main entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Enhance generated skills')
    parser.add_argument('skill_dir', help='Path to skill directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(message)s', force=True)

    # Enhance skill
    enhancer = SkillEnhancer(args.skill_dir)
    try:
        success = enhancer.enhance()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
