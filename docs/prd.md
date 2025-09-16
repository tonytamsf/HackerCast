---

## Product Requirements Document (PRD): HackerCast

### 1. **Overview & Vision** 🎯
**Product Name:** HackerCast: The Top 20 Daily

**Vision:** To provide technology professionals, developers, and enthusiasts with a convenient, audio-first way to stay informed about the most important conversations and articles trending on Hacker News. We transform the day's top 20 stories into a bite-sized daily podcast, making it easy to catch up during commutes, workouts, or any screen-free time.

### 2. **Problem Statement & Target Audience** 🧑‍💻
**Problem:** Keeping up with the fast-paced world of technology is crucial but time-consuming. Hacker News is a primary source for what's new and important, but it requires active reading and sifting through comment threads. Busy professionals often lack the dedicated screen time to do this effectively every day.

**Target Audience:**
* Software Developers & Engineers
* Product Managers & Tech Executives
* Startup Founders & Venture Capitalists
* Computer Science Students
* Anyone with a keen interest in the tech industry.

### 3. **Features & Requirements (MVP)**
This PRD focuses on the Minimum Viable Product (MVP) to launch the service quickly.

#### **Feature 1: Data Ingestion Pipeline**
* **1.1: Fetch Top Stories:** The system must automatically fetch the list of the top 20 story IDs from the official Hacker News (HN) API at a scheduled time each day.
* **1.2: Get Story Details:** For each story ID, the system must retrieve the article's URL, title, and score.
* **1.3: Scrape Article Content:** The system must visit the article URL and scrape the core text content, stripping out ads, navigation bars, and other non-essential elements. This must be resilient to different website layouts.

#### **Feature 2: Content Generation Engine**
* **2.1: NotebookLM Integration:** The system will use NotebookLM as its core summarization and script-writing engine.
* **2.2: Sourcing:** For each of the 20 articles, the scraped text will be provided as a source to NotebookLM.
* **2.3: Script Generation Prompt:** A standardized, well-engineered prompt will be used to instruct NotebookLM to generate a conversational podcast script. The prompt will request:
    * A brief, engaging introduction mentioning the article title.
    * A summary of the key points and arguments of the article.
    * A concluding sentence.
    * The total script length should target an audio duration of **3-5 minutes**.
    * The output must be clean text, ready for a text-to-speech (TTS) engine.

#### **Feature 3: Audio Production & Hosting**
* **3.1: Text-to-Speech (TTS) Conversion:** Each of the 20 generated scripts will be converted into high-quality audio files (MP3 format) using a modern TTS API (e.g., Google's WaveNet or a similar service). A consistent, clear, and engaging voice will be selected.
* **3.2: Audio File Hosting:** The 20 generated MP3 files must be uploaded to a publicly accessible cloud storage solution (e.g., Google Cloud Storage or AWS S3).
* **3.3: Naming Convention:** Audio files must follow a consistent naming convention for easy reference (e.g., `YYYY-MM-DD-HN-rank-story-title.mp3`).

#### **Feature 4: Podcast Feed Publishing**
* **4.1: RSS Feed Generation:** The system must dynamically generate a standard RSS 2.0 XML file formatted for podcast directories.
* **4.2: RSS Feed Content:** The feed will contain:
    * Podcast-level metadata: Title (HackerCast), description, cover art, language.
    * Episode-level metadata for each of the 20 stories: Episode title (from the article title), publication date, a short description (summary), and a direct URL to the hosted MP3 file.
* **4.3: Daily Update:** The RSS feed must be overwritten/updated daily with the latest 20 episodes.

### 4. **Success Metrics** 📈
* **Operational:** Successful daily generation and publication of all 20 episodes with >99% uptime.
* **Engagement:** Number of RSS feed subscribers and daily episode downloads.
* **Quality:** Positive ratings and reviews on podcast platforms (Apple Podcasts, Spotify, etc.).

### 5. **Out of Scope for MVP**
* A dedicated website or mobile application.
* User comments or community features.
* Multiple voice hosts or language options.
* Episode transcripts.
* Monetization or advertisements.

---

## Implementation Plan

This plan is broken into three phases, designed for an agile development approach.

### **Phase 1: Proof of Concept (PoC) - The "Manual" End-to-End**
**Goal:** Verify that the core technologies can produce a single, high-quality podcast episode.
**Timeline:** ~1 week

* **Step 1: Data Gathering:** Manually select one top article from Hacker News. Copy its URL and scrape the text using a simple Python script (`requests` and `BeautifulSoup`).
* **Step 2: Script Generation:** Manually create a new notebook in NotebookLM. Upload the scraped text as a source. Use a series of prompts to refine the output until a satisfactory podcast script is generated. **This step is critical for developing the final automated prompt.**
* **Step 3: Audio Generation:** Copy the final script and paste it into a TTS service's web interface (e.g., Google Text-to-Speech) to generate and download an MP3 file.
* **Step 4: Feed Creation:** Manually write a simple RSS XML file. Upload the MP3 to a cloud storage bucket and link to it in the XML. Test the RSS feed by adding it to a podcast app (like Pocket Casts) to confirm it works.

### **Phase 2: Automation & MVP Build**
**Goal:** Build the automated, serverless pipeline that runs daily.
**Timeline:** ~3-4 weeks

* **Tech Stack:**
    * **Orchestration:** Google Cloud Functions (or AWS Lambda) triggered by a daily scheduler (Cloud Scheduler).
    * **Language:** Python.
    * **APIs:** Hacker News API, Google Text-to-Speech API.
    * **Automation:** **A key challenge is that NotebookLM does not have a public API.** The initial implementation will rely on a browser automation tool like **Puppeteer** or **Selenium** to programmatically upload sources and run the prompt. This is the most fragile part of the system and will be replaced if/when an official API becomes available.
    * **Storage:** Google Cloud Storage (or AWS S3).
* **Workflow:**
    1.  **Trigger (Daily @ 5 AM UTC):** A scheduler triggers the main cloud function.
    2.  **Fetch & Scrape:** The function calls the HN API to get the top 20 story URLs and then loops through them, scraping the content of each.
    3.  **Generate Scripts (Loop x20):**
        * The function launches a headless browser instance (Puppeteer).
        * It navigates to NotebookLM, creates a new notebook, uploads the scraped text as a source, and inputs the master prompt.
        * It extracts the resulting text script.
    4.  **Generate Audio (Loop x20):**
        * The function sends the script to the TTS API.
        * The returned MP3 audio is saved directly to a cloud storage bucket.
    5.  **Generate & Publish RSS:**
        * After all 20 audio files are created, the function generates a new `podcast.xml` file.
        * It lists all 20 new episodes with their metadata and links to the MP3s in the storage bucket.
        * This XML file is uploaded to the public storage bucket, overwriting the previous day's feed.

### **Phase 3: Launch & Iterate**
**Goal:** Distribute the podcast and begin gathering feedback for improvements.
**Timeline:** Ongoing

* **Step 1: Submission:** Submit the public URL of the `podcast.xml` RSS feed to major podcast directories: Apple Podcasts, Spotify, Google Podcasts, etc.
* **Step 2: Monitoring:** Implement logging and alerting (e.g., Cloud Monitoring) to be notified if any part of the daily pipeline fails (e.g., a website scrape breaks, an API call fails).
* **Step 3: Iteration:** Based on listener feedback and observation:
    * Refine the NotebookLM master prompt to improve script quality, tone, or structure.
    * Experiment with different TTS voices.
    * Improve the robustness of the article scraper.
    * Begin planning for V2 features from the "Out of Scope" list, such as transcripts.