# SAP Help Portal Integration

This document explains how to scrape SAP Help Portal documentation using the custom SAP Help scraper extension.

## Overview

SAP Help Portal uses client-side rendering (Vue.js), which makes traditional web scraping impossible. However, SAP provides a JSON API that returns the full table of contents and page content.

This extension adds support for scraping SAP Help Portal documentation by:
1. Fetching the table of contents via the JSON API
2. Extracting all page IDs from the hierarchical TOC
3. Fetching each page's HTML content from the API
4. Parsing and building a standard Cline skill

## API Pattern

SAP Help Portal API endpoint:
```
https://help.sap.com/http.svc/pagecontent?deliverableInfo=1&deliverable_id={id}&buildNo={build}&file_path={page}.html
```

### Parameters:
- **deliverable_id**: Product documentation ID (e.g., `23708722` for SAP CDC)
- **buildNo**: Documentation build version (e.g., `1365`)
- **file_path**: Individual page ID (e.g., `228cd8bc68dc477094b3e0e9fe108e23.html`)

### Response Structure:
```json
{
  "status": "OK",
  "data": {
    "deliverable": {
      "title": "SAP Customer Data Cloud",
      "fullToc": [
        {
          "t": "Page Title",
          "u": "page-id.html",
          "c": [/* child pages */]
        }
      ]
    },
    "body": "<!DOCTYPE html>... full page content ..."
  }
}
```

## Finding Deliverable ID and Build Number

### Method 1: From Browser URL
When viewing SAP documentation, the URL contains the deliverable ID:
```
https://help.sap.com/docs/SAP_CUSTOMER_DATA_CLOUD/8b8d6fffe113457094a17701f63e3d6a/...
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                            This is the deliverable LOIO
```

Then inspect the network tab to find the API call with `deliverable_id` and `buildNo`.

### Method 2: From API Response
Make a test API call with any page from the documentation:
```bash
curl "https://help.sap.com/http.svc/pagecontent?deliverableInfo=1&deliverable_id=23708722&buildNo=1365&file_path=4d83300f0ac949828f9604a8abb44065.html"
```

The response will contain the correct `deliverable_id` and build information.

## Usage

### Basic Usage

```bash
cd Skill_Seekers
source venv/bin/activate

# Scrape SAP CDC documentation (10 pages for testing)
python3 -m skill_seekers.cli.sap_help_scraper \
  --deliverable-id 23708722 \
  --build-no 1365 \
  --name sap-cdc-api \
  --max-pages 10

# Build the skill
skill-seekers scrape --name sap-cdc-api --url https://help.sap.com/docs/SAP_CUSTOMER_DATA_CLOUD/ --skip-scrape

# Package the skill
skill-seekers package output/sap-cdc-api/
```

### Full Documentation Scrape

```bash
# Scrape all 1,139 pages (will take ~10-15 minutes)
python3 -m skill_seekers.cli.sap_help_scraper \
  --deliverable-id 23708722 \
  --build-no 1365 \
  --name sap-cdc-api \
  --max-pages 1139 \
  --rate-limit 0.3

# Build and enhance
skill-seekers scrape --name sap-cdc-api --url https://help.sap.com/docs/SAP_CUSTOMER_DATA_CLOUD/ --skip-scrape
skill-seekers enhance output/sap-cdc-api/
skill-seekers package output/sap-cdc-api/
```

### Command-Line Options

```
--deliverable-id    SAP deliverable ID (required)
--build-no          Documentation build number (required)
--name              Skill name (required)
--max-pages         Maximum pages to scrape (default: 100)
--rate-limit        Delay between requests in seconds (default: 0.5)
--verbose, -v       Enable verbose output
```

## Complete Workflow

### 1. Scrape SAP Documentation

```bash
cd Skill_Seekers
source venv/bin/activate

# Scrape with custom SAP scraper
python3 -m skill_seekers.cli.sap_help_scraper \
  --deliverable-id 23708722 \
  --build-no 1365 \
  --name sap-cdc-api \
  --max-pages 50
```

**Output:**
- `output/sap-cdc-api_data/` - Scraped JSON files
- `output/sap-cdc-api_data/summary.json` - Scraping summary

### 2. Build Skill

```bash
# Build skill from scraped data
skill-seekers scrape --name sap-cdc-api --url https://help.sap.com/docs/SAP_CUSTOMER_DATA_CLOUD/ --skip-scrape
```

**Output:**
- `output/sap-cdc-api/SKILL.md` - Main skill file
- `output/sap-cdc-api/references/` - Documentation files

### 3. Enhance (Optional)

```bash
# Enhance with Claude (local or API)
skill-seekers enhance output/sap-cdc-api/
```

### 4. Package

```bash
# Package to ZIP
skill-seekers package output/sap-cdc-api/
```

**Output:**
- `output/sap-cdc-api.zip` - Ready to upload to Cline

### 5. Deploy to cdc-specs (Optional)

```bash
# Return to SkillsPOC root
cd ..

# Deploy to cdc-specs repository
./deploy-skills-to-cdc.sh sap-cdc-api

# Commit to cdc-specs
cd /Users/I347329/Library/CloudStorage/OneDrive-SAPSE/Documents/GitHub/cdc-specs
git add .cline/skills/sap-cdc-api/
git commit -m "Add SAP CDC API skill"
git push
```

## Supported SAP Products

This scraper works with any SAP Help Portal documentation. Common products:

| Product | Deliverable ID | Example |
|---------|----------------|---------|
| SAP Customer Data Cloud | 23708722 | CDC API, Authentication |
| SAP BTP | (varies) | Cloud Platform services |
| SAP S/4HANA | (varies) | ERP documentation |
| SAP Analytics Cloud | (varies) | Analytics and BI |

To find the deliverable ID for other products:
1. Navigate to the documentation in your browser
2. Open browser DevTools (F12)
3. Go to Network tab
4. Look for API calls to `pagecontent`
5. Extract `deliverable_id` and `buildNo` from the request

## Performance Considerations

### Scraping Speed
- **Rate Limit**: Default 0.5s between requests (recommended)
- **Pages per minute**: ~120 pages/minute with default rate limit
- **Full documentation**: 1,139 pages ≈ 10-15 minutes

### Optimization Tips

1. **Start Small**: Test with `--max-pages 10` first
2. **Adjust Rate Limit**: Use `--rate-limit 0.3` for faster scraping (be respectful)
3. **Parallel Processing**: Not currently supported (API limitation)
4. **Caching**: Scraped data is cached in `output/{name}_data/`

## Troubleshooting

### Error: 404 Not Found

**Problem**: Invalid deliverable ID or build number

**Solution**: 
1. Verify the deliverable ID from the browser URL
2. Check the build number in the API response
3. Try with a known working page first

### Error: Empty Content

**Problem**: Page has no extractable content

**Solution**:
- Some pages are navigation-only (no content)
- The scraper automatically skips pages with <50 characters
- This is normal behavior

### Error: Rate Limiting

**Problem**: Too many requests too quickly

**Solution**:
- Increase `--rate-limit` to 1.0 or higher
- SAP Help Portal is generally permissive, but be respectful

## Architecture

### File Structure

```
Skill_Seekers/
└── src/skill_seekers/cli/
    └── sap_help_scraper.py    # SAP Help Portal scraper
```

### Class: SAPHelpScraper

**Methods:**
- `fetch_toc()` - Fetch table of contents from API
- `extract_page_ids()` - Recursively extract all page IDs
- `fetch_page_content()` - Fetch individual page HTML
- `parse_html_content()` - Parse HTML and extract structured data
- `save_page()` - Save page to JSON file
- `scrape_all()` - Main scraping orchestration

### Integration with SkillSeekers

The SAP scraper outputs data in the same format as the standard doc_scraper:
- JSON files in `output/{name}_data/pages/`
- Summary file in `output/{name}_data/summary.json`
- Compatible with existing skill building pipeline

## Example: SAP CDC API Skill

### Scrape Command
```bash
python3 -m skill_seekers.cli.sap_help_scraper \
  --deliverable-id 23708722 \
  --build-no 1365 \
  --name sap-cdc-api \
  --max-pages 100
```

### Output Statistics
- **Total pages in documentation**: 1,139
- **Pages scraped**: 100
- **Categories**: API Reference, Authentication, User Management
- **Code samples**: REST API examples, JavaScript SDK
- **Build time**: ~2 minutes (scraping) + 30 seconds (building)

### Skill Structure
```
sap-cdc-api/
├── SKILL.md              # Main skill file
├── references/
│   ├── index.md          # Navigation
│   ├── api_reference.md  # REST API docs
│   ├── authentication.md # Auth methods
│   └── user_management.md# User APIs
├── scripts/              # Helper scripts
└── assets/               # Templates
```

## Future Enhancements

### Planned Features
1. **Auto-discovery**: Automatically find deliverable ID from URL
2. **Category Detection**: Better categorization based on SAP structure
3. **Multi-language**: Support for non-English documentation
4. **Incremental Updates**: Only scrape changed pages
5. **CLI Integration**: Add `skill-seekers sap-help` command

### Contributing

To extend this scraper:
1. Fork the SkillSeekers repository
2. Modify `src/skill_seekers/cli/sap_help_scraper.py`
3. Test with your SAP documentation
4. Submit a pull request

## References

- [SAP Help Portal](https://help.sap.com/)
- [SAP Customer Data Cloud Documentation](https://help.sap.com/docs/SAP_CUSTOMER_DATA_CLOUD)
- [SkillSeekers GitHub](https://github.com/yusufkaraaslan/Skill_Seekers)
- [Cline Skills Documentation](https://docs.cline.bot/features/skills)

---

**Last Updated**: January 16, 2026
**Version**: 1.0.0
**Author**: SkillsPOC Team
