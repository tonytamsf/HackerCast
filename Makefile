# Makefile for HackerCast

# Default number of stories to process
LIMIT ?= 20
# Default repository, can be overridden.
# In GitHub Actions, this will be provided by the workflow.
REPO ?= "TonyTam/HackerCast"
BASE_URL ?= "https://raw.githubusercontent.com/$(REPO)/main/output"

# Phony targets prevent conflicts with files of the same name
.PHONY: all install audio rss clean

# The default target, executed when you run `make`
all: audio rss

# Sets up the development environment
install:
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -r requirements.txt

# Generates the podcast audio file
# Usage: make audio [LIMIT=N]
audio:
	. venv/bin/activate; python main.py run --limit $(LIMIT)

# Generates the RSS feed
# Usage: make rss [REPO=owner/repo]
rss:
	. venv/bin/activate; python rss_generator.py --output-dir output --output-file output/rss.xml --base-url $(BASE_URL)

# Removes generated files
clean:
	rm -rf output/audio/*
	rm -rf output/data/*
	rm -f output/rss.xml
