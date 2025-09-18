#!/usr/bin/env python3
"""
Script to upload new HackerCast episodes to GitHub Pages using gh CLI.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import argparse

def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result

def upload_episode(episode_path, commit_message=None):
    """Upload a new episode to GitHub Pages."""
    episode_path = Path(episode_path)

    if not episode_path.exists():
        print(f"Error: Episode file {episode_path} does not exist")
        return False

    if not episode_path.suffix.lower() == '.mp3':
        print(f"Error: {episode_path} is not an MP3 file")
        return False

    # Ensure we're on the github-pages branch
    current_branch = subprocess.run(['git', 'branch', '--show-current'],
                                  capture_output=True, text=True).stdout.strip()

    if current_branch != 'github-pages':
        print(f"Switching from {current_branch} to github-pages branch...")
        run_command(['git', 'checkout', 'github-pages'])

    # Create episodes directory if it doesn't exist
    episodes_dir = Path('episodes')
    episodes_dir.mkdir(exist_ok=True)

    # Copy episode to episodes directory
    target_path = episodes_dir / episode_path.name
    print(f"Copying {episode_path} to {target_path}")
    shutil.copy2(episode_path, target_path)

    # Stage the new episode
    run_command(['git', 'add', str(target_path)])

    # Check if there are changes to commit
    status_result = run_command(['git', 'status', '--porcelain'], check=False)
    if not status_result.stdout.strip():
        print("No changes to commit")
        return True

    # Create commit message
    if not commit_message:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        commit_message = f"Add new HackerCast episode: {episode_path.name} ({timestamp})"

    # Commit the change
    run_command(['git', 'commit', '-m', commit_message])

    # Push to GitHub (this will trigger the GitHub Pages deployment)
    print("Pushing to GitHub...")
    run_command(['git', 'push', 'origin', 'github-pages'])

    print(f"✅ Episode {episode_path.name} uploaded successfully!")
    print(f"📡 RSS feed will be updated automatically")
    print(f"🌐 Episode will be available at: https://tonytamsf.github.io/HackerCast/episodes/{episode_path.name}")

    return True

def main():
    parser = argparse.ArgumentParser(description='Upload HackerCast episode to GitHub Pages')
    parser.add_argument('episode', help='Path to the MP3 episode file')
    parser.add_argument('-m', '--message', help='Custom commit message')

    args = parser.parse_args()

    success = upload_episode(args.episode, args.message)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()