#!/usr/bin/env python3
"""
AI Summarizer for Skills
Uses SAP AI Core to intelligently summarize documentation for overview skills.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AISummarizer:
    """Summarizes documentation using SAP AI Core."""

    def __init__(self, config_path: str = None):
        """
        Initialize AI summarizer.

        Args:
            config_path: Path to .env file with SAP AI Core credentials
        """
        # Look for config in project first, then home directory
        if config_path:
            self.config_path = config_path
        else:
            # Try project directory first
            project_config = os.path.join(os.getcwd(), 'Skill_Seekers', 'ai_config.env')
            home_config = os.path.join(Path.home(), '.skillseekers', 'ai_config.env')

            if os.path.exists(project_config):
                self.config_path = project_config
            else:
                self.config_path = home_config

        self.config = self._load_config()

    def _load_config(self) -> Dict[str, str]:
        """Load SAP AI Core configuration from .env file."""
        config = {
            'AI_CORE_URL': os.getenv('SAP_AI_CORE_URL', ''),
            'AI_CORE_CLIENT_ID': os.getenv('SAP_AI_CORE_CLIENT_ID', ''),
            'AI_CORE_CLIENT_SECRET': os.getenv('SAP_AI_CORE_CLIENT_SECRET', ''),
            'AI_CORE_AUTH_URL': os.getenv('SAP_AI_CORE_AUTH_URL', ''),
            'AI_CORE_RESOURCE_GROUP': os.getenv('SAP_AI_CORE_RESOURCE_GROUP', 'default'),
            'AI_MODEL': os.getenv('SAP_AI_MODEL', 'gpt-4'),
        }

        # Try to load from .env file if exists
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip().strip('"').strip("'")

        return config

    def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token from SAP AI Core."""
        if not self.config['AI_CORE_AUTH_URL'] or not self.config['AI_CORE_CLIENT_ID']:
            logger.warning("SAP AI Core credentials not configured")
            return None

        try:
            response = requests.post(
                self.config['AI_CORE_AUTH_URL'],
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.config['AI_CORE_CLIENT_ID'],
                    'client_secret': self.config['AI_CORE_CLIENT_SECRET'],
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    def summarize_pages(self, pages: List[Dict[str, Any]],
                       skill_name: str,
                       max_length: int = 5000) -> str:
        """
        Summarize multiple pages into concise overview.

        Args:
            pages: List of page dictionaries with content
            skill_name: Name of the skill being created
            max_length: Maximum length of summary in characters

        Returns:
            Summarized content as markdown
        """
        if not self._is_configured():
            logger.warning("AI summarization not configured, using fallback")
            return self._fallback_summarize(pages, max_length)

        # Get access token
        token = self._get_access_token()
        if not token:
            logger.warning("Could not get access token, using fallback")
            return self._fallback_summarize(pages, max_length)

        # Prepare content for summarization
        content = self._prepare_content(pages)

        # Create prompt
        prompt = self._create_summary_prompt(content, skill_name, max_length)

        # Call SAP AI Core
        try:
            summary = self._call_ai_core(prompt, token)
            logger.info("✅ AI summarization successful")
            return summary
        except Exception as e:
            logger.error(f"AI summarization failed: {e}, using fallback")
            return self._fallback_summarize(pages, max_length)

    def _is_configured(self) -> bool:
        """Check if SAP AI Core is properly configured."""
        required = ['AI_CORE_URL', 'AI_CORE_CLIENT_ID', 'AI_CORE_CLIENT_SECRET']
        return all(self.config.get(key) for key in required)

    def _prepare_content(self, pages: List[Dict[str, Any]]) -> str:
        """Prepare page content for AI summarization."""
        content_parts = []

        for page in pages:
            title = page.get('title', 'Untitled')
            content = page.get('content', '')
            headings = page.get('headings', [])

            # Add page with structure
            page_text = f"## {title}\n\n"

            # Add main headings
            if headings:
                page_text += "### Key Topics:\n"
                for h in headings[:5]:  # Limit to top 5 headings
                    page_text += f"- {h['text']}\n"
                page_text += "\n"

            # Add content (truncate if too long)
            if len(content) > 1000:
                content = content[:1000] + "..."
            page_text += content + "\n\n"

            content_parts.append(page_text)

        return "\n".join(content_parts)

    def _create_summary_prompt(self, content: str, skill_name: str,
                              max_length: int) -> str:
        """Create prompt for AI summarization."""

        # Detect if this is a role-based skill (contains "writer", "architect", "expert", "implementer", etc.)
        role_keywords = ['writer', 'architect', 'expert', 'implementer', 'specialist', 'handler']
        is_role_based = any(keyword in skill_name.lower() for keyword in role_keywords)

        if is_role_based:
            return f"""You are an expert technical writer creating a practical, role-based skill guide.

Task: Create a "{skill_name}" skill that teaches developers HOW to accomplish specific tasks, not just WHAT the API does.

Source Documentation:
{content}

Requirements:
1. Focus on PATTERNS and HOW-TO, not just documentation
2. Include 3-5 practical code examples that developers can copy-paste
3. Show authentication patterns with working code
4. Include error handling patterns with examples
5. Add troubleshooting section with common issues and solutions
6. Include best practices with code examples
7. Keep total length under {max_length} characters
8. Use clear markdown formatting

Structure:
# [Skill Name]
[One-line description of what this skill teaches]

## When to Use This Skill
[List specific scenarios when this skill is triggered]

## Authentication Patterns
[2-3 patterns with working code examples]

## Request/Response Patterns
[Show how to format requests and handle responses]

## Error Handling
[Common errors and how to handle them with code]

## Best Practices
[5 best practices with code examples]

## Quick Troubleshooting
[Common issues and solutions]

## Testing Guide
[How to test the implementation]

Output ONLY the markdown content, no explanations."""
        else:
            # Original prompt for documentation-focused skills
            return f"""You are an expert technical writer creating concise API documentation.

Task: Create a focused overview skill for "{skill_name}" that will help developers quickly understand the API.

Source Documentation:
{content}

Requirements:
1. Extract ONLY the most important general concepts (authentication, request/response format, error handling)
2. Create a namespace directory showing which APIs are available
3. Include essential code examples (keep them SHORT)
4. Remove ALL marketing text, redundant explanations, and verbose notes
5. Focus on actionable information developers need
6. Keep total length under {max_length} characters
7. Use clear markdown formatting

Structure:
# API Overview
[Brief introduction]

## Key Concepts
[Authentication, Response Format, Error Handling - keep concise]

## API Namespaces
[List of available namespaces with one-line descriptions]

## Quick Reference
[Essential parameters, common patterns]

Output ONLY the markdown content, no explanations."""

    def _call_ai_core(self, prompt: str, token: str) -> str:
        """Call SAP AI Core API for summarization."""
        url = f"{self.config['AI_CORE_URL']}/v2/inference/deployments"

        headers = {
            'Authorization': f'Bearer {token}',
            'AI-Resource-Group': self.config['AI_CORE_RESOURCE_GROUP'],
            'Content-Type': 'application/json',
        }

        payload = {
            'model': self.config['AI_MODEL'],
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 2000,
            'temperature': 0.3,  # Lower temperature for more focused output
        }

        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']

    def _fallback_summarize(self, pages: List[Dict[str, Any]],
                           max_length: int) -> str:
        """Fallback summarization when AI is not available."""
        logger.info("Using rule-based fallback summarization")

        summary_parts = []

        # Extract key information from pages
        for page in pages[:5]:  # Limit to first 5 pages
            title = page.get('title', '')
            content = page.get('content', '')
            headings = page.get('headings', [])

            if title:
                summary_parts.append(f"## {title}\n")

            # Add first paragraph only
            paragraphs = content.split('\n\n')
            if paragraphs:
                first_para = paragraphs[0][:500]  # Limit length
                summary_parts.append(f"{first_para}\n")

            # Add key headings
            if headings:
                for h in headings[:3]:
                    summary_parts.append(f"- {h['text']}\n")

            summary_parts.append("\n")

        summary = "\n".join(summary_parts)

        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "\n\n[Content truncated...]"

        return summary


def create_config_template(output_path: str = None):
    """Create a template .env file for SAP AI Core configuration."""
    if not output_path:
        config_dir = os.path.join(Path.home(), '.skillseekers')
        os.makedirs(config_dir, exist_ok=True)
        output_path = os.path.join(config_dir, 'ai_config.env')

    template = """# SAP AI Core Configuration for SkillSeekers
# Fill in your SAP AI Core credentials below

# SAP AI Core API URL
SAP_AI_CORE_URL=https://api.ai.prod.eu-central-1.aws.ml.hana.ondemand.com

# OAuth2 Authentication URL
SAP_AI_CORE_AUTH_URL=https://your-subdomain.authentication.eu10.hana.ondemand.com/oauth/token

# Client Credentials
SAP_AI_CORE_CLIENT_ID=your-client-id
SAP_AI_CORE_CLIENT_SECRET=your-client-secret

# Resource Group (default: 'default')
SAP_AI_CORE_RESOURCE_GROUP=default

# AI Model to use (default: 'gpt-4')
SAP_AI_MODEL=gpt-4

# How to get these credentials:
# 1. Go to SAP BTP Cockpit
# 2. Navigate to your AI Core instance
# 3. Create a service key
# 4. Copy the credentials from the service key JSON
"""

    with open(output_path, 'w') as f:
        f.write(template)

    logger.info(f"✅ Created config template: {output_path}")
    logger.info("📝 Please fill in your SAP AI Core credentials")

    return output_path


if __name__ == "__main__":
    # Create config template
    import argparse

    parser = argparse.ArgumentParser(description='AI Summarizer Configuration')
    parser.add_argument('--create-config', action='store_true',
                       help='Create configuration template')
    parser.add_argument('--test', action='store_true',
                       help='Test AI summarization')

    args = parser.parse_args()

    if args.create_config:
        path = create_config_template()
        print(f"Config template created: {path}")

    if args.test:
        summarizer = AISummarizer()
        test_pages = [
            {
                'title': 'Test Page',
                'content': 'This is test content for AI summarization.',
                'headings': [{'text': 'Test Heading', 'level': 'h2'}]
            }
        ]
        result = summarizer.summarize_pages(test_pages, 'test-skill')
        print("Summary:", result)
