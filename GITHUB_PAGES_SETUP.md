# HackerCast GitHub Pages Setup

This document describes the GitHub Pages hosting setup for HackerCast RSS feeds and podcast episodes.

## 📋 Overview

HackerCast now uses GitHub Pages to host:
- RSS feed for podcast distribution
- Audio episode files (MP3)
- Simple website homepage
- Automatic deployment via GitHub Actions

## 🏗️ Architecture

```
HackerCast/
├── episodes/                    # Audio files directory
│   ├── README.md
│   └── *.mp3                   # Episode files
├── index.html                  # Website homepage
├── rss.xml                     # RSS feed (auto-generated)
├── episodes.json               # Episode metadata (auto-generated)
├── upload_episode.py           # Upload script
├── scripts/
│   └── setup_github_pages.sh  # Setup automation
└── .github/workflows/
    └── github-pages.yml        # Deployment workflow
```

## 🌐 Live URLs

- **RSS Feed:** https://tonytamsf.github.io/HackerCast/rss.xml
- **Website:** https://tonytamsf.github.io/HackerCast/
- **Episodes Directory:** https://tonytamsf.github.io/HackerCast/episodes/

## 🚀 GitHub Actions Workflow

The `github-pages.yml` workflow automatically:

1. **Triggers on:**
   - Push to `github-pages` branch
   - Daily at 6 AM UTC (via cron)
   - Manual workflow dispatch

2. **Actions performed:**
   - Copies audio files from `output/audio/` to `episodes/`
   - Generates RSS feed from episode files
   - Creates episode metadata JSON
   - Deploys to GitHub Pages

3. **RSS Generation:**
   - Scans `episodes/` directory for MP3 files
   - Extracts metadata using `mutagen`
   - Parses dates from filename patterns
   - Generates iTunes-compatible RSS feed

## 📱 Usage Instructions

### Upload New Episodes

#### Method 1: Upload Script (Recommended)
```bash
./upload_episode.py path/to/new_episode.mp3
```

Optional custom commit message:
```bash
./upload_episode.py path/to/episode.mp3 -m "Custom commit message"
```

#### Method 2: Manual Upload
```bash
# Copy episode to episodes directory
cp output/audio/new_episode.mp3 episodes/

# Commit and push (triggers auto-deployment)
git add episodes/new_episode.mp3
git commit -m "Add new HackerCast episode: new_episode.mp3"
git push origin github-pages
```

### Episode Filename Convention

Episodes should follow this naming pattern for automatic date parsing:
```
hackercast_YYYYMMDD_HHMMSS.mp3
```

Examples:
- `hackercast_20240917_180000.mp3` → "HackerCast - September 17, 2024"
- `hackercast_20240918_120000.mp3` → "HackerCast - September 18, 2024"

## 🔧 Setup Process

The setup was completed using these steps:

1. **Enable GitHub Pages:**
   ```bash
   gh api --method POST repos/tonytamsf/HackerCast/pages \
     --input - <<< '{"build_type":"workflow","source":{"branch":"github-pages","path":"/"}}'
   ```

2. **Create directory structure:**
   ```bash
   mkdir -p episodes
   cp output/audio/*.mp3 episodes/
   ```

3. **Deploy initial files:**
   ```bash
   git add .
   git commit -m "Set up GitHub Pages for HackerCast"
   git push origin github-pages
   ```

## 🎵 RSS Feed Features

The generated RSS feed includes:

- **iTunes-compatible tags:** Author, category, summary, duration
- **Episode metadata:** Title, description, publication date, GUID
- **Audio enclosures:** Direct links to MP3 files
- **Automatic updates:** Regenerated on every deployment

### RSS Feed Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>HackerCast</title>
    <description>Daily audio podcasts from the top Hacker News stories</description>
    <itunes:category text="Technology"/>
    <item>
      <title>HackerCast - September 17, 2024</title>
      <enclosure url="https://tonytamsf.github.io/HackerCast/episodes/episode.mp3"
                 type="audio/mpeg" length="1234567"/>
      <itunes:duration>1234</itunes:duration>
    </item>
  </channel>
</rss>
```

## 🔍 Monitoring & Maintenance

### Check Deployment Status
```bash
# View GitHub Pages deployment status
gh run list --workflow=github-pages.yml

# View specific run details
gh run view [run-id]
```

### Verify RSS Feed
```bash
# Check RSS feed validity
curl -s https://tonytamsf.github.io/HackerCast/rss.xml | head -20
```

### Episode Management
```bash
# List current episodes
ls -la episodes/

# Check episode file sizes
du -sh episodes/*.mp3
```

## 🚨 Troubleshooting

### Common Issues

1. **Large file uploads timing out:**
   - Split upload into smaller batches
   - Use Git LFS for large audio files (optional)

2. **RSS feed not updating:**
   - Check GitHub Actions workflow status
   - Verify files are in `episodes/` directory
   - Manually trigger workflow: `gh workflow run github-pages.yml`

3. **Episodes not appearing:**
   - Verify filename follows convention
   - Check file permissions and format (MP3 only)
   - Review workflow logs for errors

### GitHub Actions Logs
```bash
# View latest workflow run logs
gh run view --log

# Download workflow artifacts
gh run download [run-id]
```

## 🔒 Security Considerations

- Repository visibility: Currently private (consider public for better Pages support)
- Audio file access: Direct links via GitHub Pages
- No authentication required for RSS feed access
- Episode files are publicly accessible once deployed

## 📈 Future Enhancements

Potential improvements:
- [ ] Custom domain setup
- [ ] Podcast artwork/cover image
- [ ] Episode chapters/timestamps
- [ ] Analytics integration
- [ ] CDN optimization for large files
- [ ] Automated episode cleanup (archive old episodes)

## 🛠️ Dependencies

The GitHub Actions workflow requires:
- `feedgen` - RSS feed generation
- `mutagen` - Audio metadata extraction
- Python 3.11+

## 📞 Support

For issues with this setup:
1. Check GitHub Actions workflow logs
2. Verify file formats and naming conventions
3. Review GitHub Pages settings in repository
4. Test RSS feed validity with online validators