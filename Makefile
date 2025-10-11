# Makefile for HackerCast

# Default number of stories to process
LIMIT ?= 20
# Default repository, can be overridden.
# In GitHub Actions, this will be provided by the workflow.
REPO ?= tonytamsf/HackerCast
BASE_URL ?= https://raw.githubusercontent.com/$(REPO)/main/output

# Detect if we're in CI environment (GitHub Actions sets CI=true)
# In CI, use Python directly; locally, use venv
ifdef CI
    PYTHON := python
    PIP := pip
else
    PYTHON := . venv/bin/activate && python
    PIP := . venv/bin/activate && pip
endif

# Phony targets prevent conflicts with files of the same name
.PHONY: all install audio rss clean

# The default target, executed when you run `make`
all: audio rss

# Sets up the development environment
install:
ifndef CI
	test -d venv || python3 -m venv venv
endif
	$(PIP) install -r requirements.txt

# Generates the podcast audio file
# Usage: make audio [LIMIT=N]
audio:
	$(PYTHON) main.py run --limit $(LIMIT)

# Generates the RSS feed
# Usage: make rss [REPO=owner/repo]
rss:
	$(PYTHON) rss_generator.py --output-dir output --output-file output/rss.xml --base-url $(BASE_URL)

# Removes generated files
clean:
	rm -rf output/audio/*
	rm -rf output/data/*
	rm -f output/rss.xml
