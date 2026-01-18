#!/usr/bin/env python3
"""
Update doc_scraper.py to use simplified SKILL.md template
"""

import re

# Read the simple template
with open('SKILL_TEMPLATE_SIMPLE.md', 'r') as f:
    simple_template = f.read()

# Read doc_scraper.py
with open('src/skill_seekers/cli/doc_scraper.py', 'r') as f:
    content = f.read()

# Find and replace the create_enhanced_skill_md method
pattern = r'(    def create_enhanced_skill_md\(self.*?\n)(.*?)(    def \w+)'

def replacement(match):
    method_sig = match.group(1)
    next_method = match.group(3)

    new_method = f'''{method_sig}        """Create simplified SKILL.md following Cline best practices"""
        # Get description
        if 'description' not in self.config:
            description = self._infer_description_from_pages(categories)
        else:
            description = self.config['description']

        # Build doc files list
        doc_files = []
        for cat in sorted(categories.keys()):
            doc_files.append(f"- **[{cat}.md](docs/{cat}.md)** - {cat.replace('_', ' ').title()} documentation")
        doc_files_str = '\\n'.join(doc_files)

        # Use simple template
        content = """---
name: {name}
description: {description}
---

# {title} Skill

{description}

## When to Use This Skill

This skill should be triggered when:
- Working with {name} APIs or features
- Implementing {name} solutions
- Debugging {name} code
- Integrating {name} into projects

## Documentation

Comprehensive documentation is available in `docs/`:

{doc_files}

## Quick Reference

Common patterns and examples will be added here as you use the skill.

## Resources

- **docs/** - Detailed documentation with code examples
- **scripts/** - Helper scripts for common tasks
- **assets/** - Templates and example projects
"""

        # Format template
        content = content.format(
            name=self.name,
            title=self.name.replace('-', ' ').title(),
            description=description,
            doc_files=doc_files_str
        )

        filepath = os.path.join(self.skill_dir, "SKILL.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("  ✓ SKILL.md (simplified)")

    '''

    return new_method + next_method

# Apply replacement
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('src/skill_seekers/cli/doc_scraper.py', 'w') as f:
    f.write(new_content)

print("✅ Updated doc_scraper.py with simplified template")
