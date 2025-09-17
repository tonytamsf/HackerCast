# Interactive Story Selection Guide

This guide explains how to use the interactive story selection feature in HackerCast.

## Overview

The interactive story selection feature allows you to manually choose which Hacker News stories to include in your podcast. Instead of processing all top stories automatically, you can review headlines and selectively pick the most interesting ones.

## Quick Start

### Basic Usage

```bash
# Run HackerCast with interactive selection
python main.py run --interactive

# Or use the dedicated interactive command
python main.py interactive

# Select specific stories only
python main.py select --limit 10
```

### Interactive Mode

```bash
# Fetch 20 stories and select interactively
python main.py run --interactive --limit 20

# Use debug mode for more detailed output
python main.py --debug run --interactive
```

## Interface Overview

When you enter interactive selection mode, you'll see:

1. **Header**: Shows total stories, selected count, and active filters
2. **Story Table**: Displays stories with selection status, title, score, age, author, and URL indicator
3. **Command Prompt**: Available commands for navigation and selection
4. **Footer**: Quick reference for common commands

### Story Table Columns

- **#**: Story number for quick navigation
- **Sel**: Selection status (✓ = selected, ○ = unselected)
- **Title**: Story headline (truncated for display)
- **Score**: Hacker News score/points
- **Age**: How long ago the story was posted (hours/days)
- **Author**: Username who posted the story
- **URL**: Indicator (🔗 = has URL, ❌ = no URL)

## Commands Reference

### Basic Selection

| Command | Description |
|---------|-------------|
| `s`, `select` | Toggle selection of current story |
| `d`, `deselect` | Deselect current story |
| `a`, `all` | Select all filtered stories |
| `n`, `none` | Deselect all filtered stories |
| `i`, `invert` | Invert selection for filtered stories |

### Navigation

| Command | Description |
|---------|-------------|
| `<number>` | Jump to story number (e.g., `5` jumps to story #5) |
| `next`, `>` | Go to next page |
| `prev`, `<` | Go to previous page |

### Smart Selection

| Command | Description | Example |
|---------|-------------|---------|
| `score` | Select by minimum score (interactive) | Prompts for score threshold |
| `score:N` | Select stories with score ≥ N | `score:100` selects stories with 100+ points |
| `recent` | Select recent stories (interactive) | Prompts for maximum age |
| `hours:N` | Select stories newer than N hours | `hours:6` selects stories from last 6 hours |

### Filtering & Preview

| Command | Description |
|---------|-------------|
| `f`, `filter` | Set text filter (searches title and author) |
| `u`, `urls` | Toggle showing only stories with URLs |
| `p`, `preview` | Preview current story details |

### Actions

| Command | Description |
|---------|-------------|
| `c`, `confirm` | Confirm selection and proceed with processing |
| `h`, `help` | Show detailed help |
| `q`, `quit` | Cancel and quit |

## Usage Examples

### Example 1: Select High-Quality Stories

```bash
python main.py interactive --limit 30
```

1. Start with 30 stories
2. Use `score:150` to select only highly-rated stories
3. Use `u` to show only stories with URLs (scrapable content)
4. Review and manually deselect any uninteresting stories
5. Use `c` to confirm and proceed

### Example 2: Focus on Recent Content

```bash
python main.py select --limit 50
```

1. Fetch 50 recent stories
2. Use `hours:12` to select only stories from last 12 hours
3. Use `f` and search for specific topics (e.g., "AI", "Python")
4. Use `p` to preview interesting stories
5. Confirm selection

### Example 3: Curated Selection

```bash
python main.py run --interactive --limit 20
```

1. Review all 20 stories individually
2. Use `d` to deselect stories you're not interested in
3. Use `preview` to see full details of promising stories
4. Keep 5-8 high-quality stories
5. Proceed with full pipeline processing

## Tips and Best Practices

### Selection Strategy

1. **Start with Quality**: Use `score:100` to focus on well-rated stories
2. **Check Scrapability**: Use `u` to show only stories with URLs
3. **Time Relevance**: Use `hours:24` for recent content
4. **Topic Filtering**: Use `f` to search for specific keywords
5. **Manual Review**: Use `p` to preview interesting stories

### Optimal Workflow

1. **Filter First**: Apply score and time filters to reduce noise
2. **Quick Scan**: Review headlines and scores quickly
3. **Preview Interesting**: Use preview for stories you're unsure about
4. **Final Selection**: Aim for 5-10 high-quality stories for best podcast length

### Performance Considerations

- **Story Limit**: Fetching 20-50 stories provides good variety without overwhelming choice
- **Selection Size**: 5-10 selected stories typically create a 15-30 minute podcast
- **URL Requirement**: Only stories with URLs can be scraped for content

## Troubleshooting

### Common Issues

**No stories with URLs**
- Some Hacker News posts are "Ask HN" or "Show HN" without external links
- Use the `u` filter to see only scrapable stories
- Consider expanding your story limit

**Filter shows no results**
- Clear filters with the `f` command (enter empty text)
- Try broader search terms
- Check if URL filter is accidentally enabled

**Interface seems stuck**
- Press `h` for help at any time
- Use `q` to quit and restart if needed
- Check terminal size (interface needs reasonable width)

**Selection validation warnings**
- Stories without URLs cannot be scraped
- Very old stories might have dead links
- Review the warnings but proceed if you have enough valid stories

### Error Recovery

If the interactive selector encounters an error:

1. The system will ask if you want to proceed with all stories
2. Choose "yes" to continue with automatic processing
3. Choose "no" to cancel the pipeline
4. Check logs for detailed error information

## Technical Details

### Architecture

The interactive selection feature consists of:

- **StorySelection**: Data model for managing story selection state
- **SelectableStory**: Wrapper for individual stories with selection metadata
- **InteractiveStorySelector**: Rich-based terminal UI for story selection
- **Pipeline Integration**: Seamless integration with existing HackerCast workflow

### Data Flow

1. **Fetch**: Get top stories from Hacker News API
2. **Select**: Interactive selection interface
3. **Validate**: Ensure selected stories are processable
4. **Scrape**: Extract content from selected story URLs
5. **Generate**: Create podcast script and audio

### Configuration

The feature respects existing HackerCast configuration:

- `HN_MAX_STORIES`: Default story limit
- `LOG_LEVEL`: Controls debugging output
- Existing retry and timeout settings

## API Reference

### Command Line Interface

```bash
# Main commands
python main.py run --interactive [--limit N]
python main.py interactive [--limit N]
python main.py select [--limit N]

# Global options
--config CONFIG_FILE    # Custom configuration file
--debug                 # Enable debug mode
```

### Programmatic Usage

```python
from main import HackerCastPipeline

# Create pipeline
pipeline = HackerCastPipeline()

# Fetch stories
stories = pipeline.fetch_top_stories(limit=20)

# Interactive selection
selected = pipeline.select_stories_interactively(stories)

# Continue processing
content = pipeline.scrape_articles(selected)
```

## Integration with Existing Workflow

The interactive selection feature is designed to integrate seamlessly:

- **Backward Compatible**: Existing commands work unchanged
- **Optional Feature**: Only activated with `--interactive` flag
- **Fallback Graceful**: Errors fall back to automatic processing
- **Logging Integration**: Uses existing logging configuration
- **Configuration Respect**: Honors all existing settings

## Future Enhancements

Planned improvements include:

- **Keyboard Navigation**: Arrow key support for better navigation
- **Bulk Actions**: Select ranges of stories
- **Saved Filters**: Save and reuse common filter configurations
- **Preview Enhancement**: Show article summary and metadata
- **Export Options**: Save selection criteria for future use