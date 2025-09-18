#!/bin/bash

# Setup script for GitHub Pages hosting of HackerCast RSS and episodes

set -e

echo "🎧 Setting up GitHub Pages for HackerCast..."

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is required but not installed."
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ This script must be run from within the HackerCast git repository"
    exit 1
fi

# Check if user is logged in to gh CLI
if ! gh auth status &> /dev/null; then
    echo "❌ Please login to GitHub CLI first:"
    echo "gh auth login"
    exit 1
fi

# Get repository information
REPO_OWNER=$(gh repo view --json owner --jq '.owner.login')
REPO_NAME=$(gh repo view --json name --jq '.name')

echo "📁 Repository: $REPO_OWNER/$REPO_NAME"

# Check if repository is private and warn about GitHub Pages limitations
REPO_VISIBILITY=$(gh repo view --json visibility --jq '.visibility')
if [ "$REPO_VISIBILITY" = "PRIVATE" ]; then
    echo "⚠️  Warning: Repository is private. GitHub Pages may have limitations."
    echo "Consider making the repository public for better GitHub Pages support."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Enable GitHub Pages if not already enabled
echo "🔧 Configuring GitHub Pages..."

# Try to get current pages configuration
PAGES_STATUS=$(gh api repos/$REPO_OWNER/$REPO_NAME/pages 2>/dev/null || echo "not_found")

if [ "$PAGES_STATUS" = "not_found" ]; then
    echo "📄 Enabling GitHub Pages..."

    # Enable GitHub Pages with GitHub Actions source
    gh api --method POST repos/$REPO_OWNER/$REPO_NAME/pages \
        --field source='{"branch":"github-pages","path":"/"}' \
        --field build_type="workflow" || {
        echo "❌ Failed to enable GitHub Pages"
        echo "You may need to enable it manually in the repository settings"
        echo "Go to: https://github.com/$REPO_OWNER/$REPO_NAME/settings/pages"
    }
else
    echo "✅ GitHub Pages is already enabled"
fi

# Check if we're on the correct branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "github-pages" ]; then
    echo "🔄 Switching to github-pages branch..."

    # Check if github-pages branch exists
    if git show-ref --verify --quiet refs/heads/github-pages; then
        git checkout github-pages
    else
        echo "Creating new github-pages branch..."
        git checkout -b github-pages
    fi
fi

# Create episodes directory if it doesn't exist
mkdir -p episodes

# Check if there are any episodes in output/audio to copy
if [ -d "output/audio" ] && [ "$(ls -A output/audio)" ]; then
    echo "📁 Copying existing episodes from output/audio..."
    cp output/audio/*.mp3 episodes/ 2>/dev/null || true
fi

# Add and commit any new files
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 Committing GitHub Pages setup..."
    git add .
    git commit -m "Set up GitHub Pages for HackerCast RSS and episodes hosting

🎧 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
fi

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push origin github-pages

echo ""
echo "✅ GitHub Pages setup complete!"
echo ""
echo "📡 Your HackerCast RSS feed will be available at:"
echo "   https://$REPO_OWNER.github.io/$REPO_NAME/rss.xml"
echo ""
echo "🎵 Episodes will be hosted at:"
echo "   https://$REPO_OWNER.github.io/$REPO_NAME/episodes/"
echo ""
echo "🌐 Main page:"
echo "   https://$REPO_OWNER.github.io/$REPO_NAME/"
echo ""
echo "📚 To upload new episodes, use:"
echo "   ./upload_episode.py path/to/episode.mp3"
echo ""
echo "Note: It may take a few minutes for GitHub Pages to deploy your site."