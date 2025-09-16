#!/usr/bin/env python

import requests
import sys
from bs4 import BeautifulSoup
from goose3 import Goose

def scrape_article_bs(url):
    """Scrapes the text content of an article from a given URL using BeautifulSoup."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        # Get text
        text = soup.get_text()

        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

def scrape_article_goose(url):
    """Scrapes the text content of an article from a given URL using Goose3."""
    try:
        g = Goose()
        article = g.extract(url=url)
        return article.cleaned_text
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <URL> [--scraper=bs|goose]")
        sys.exit(1)

    url = sys.argv[1]
    scraper = "goose"  # Default to goose

    if len(sys.argv) > 2:
        scraper_arg = sys.argv[2]
        if scraper_arg.startswith("--scraper="):
            scraper = scraper_arg.split("=")[1]

    if scraper == "goose":
        article_text = scrape_article_goose(url)
    elif scraper == "bs":
        article_text = scrape_article_bs(url)
    else:
        print(f"Unknown scraper: {scraper}", file=sys.stderr)
        sys.exit(1)

    print(article_text)