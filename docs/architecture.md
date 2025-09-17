# HackerCast System Architecture

## Executive Summary

HackerCast is a serverless, event-driven system designed to automatically generate daily audio podcasts from the top 20 Hacker News stories. The architecture leverages Google Cloud Platform services to provide a scalable, cost-effective solution that processes content in parallel and handles failures gracefully.

## System Overview

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud         │    │   HN API        │    │   Content       │
│   Scheduler     │───▶│   Fetcher       │───▶│   Processor     │
│   (Daily 5AM)   │    │   Function      │    │   Function      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Podcast       │◀───│   Audio         │◀───│   Script        │
│   Publisher     │    │   Generator     │    │   Generator     │
│   Function      │    │   Function      │    │   Function      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Cloud         │    │   Cloud         │    │   Cloud         │
│   Storage       │    │   Storage       │    │   Firestore     │
│   (RSS Feed)    │    │   (Audio Files) │    │   (Metadata)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

1. **HN API Fetcher**: Retrieves top story IDs from Hacker News API
2. **Content Processor**: Scrapes article content and extracts text
3. **Script Generator**: Uses browser automation to interact with NotebookLM
4. **Audio Generator**: Converts scripts to MP3 using Google Text-to-Speech
5. **Podcast Publisher**: Creates RSS feed and publishes to storage

## Component Architecture

### 1. HN API Fetcher Function

**Purpose**: Entry point that fetches top 20 story IDs from Hacker News API

**Trigger**: Cloud Scheduler (daily at 5:00 AM UTC)

**Flow**:
```
Cloud Scheduler → HN API Fetcher → Content Processor (via Pub/Sub)
```

**Technologies**:
- Google Cloud Functions (2nd gen)
- Cloud Scheduler
- Cloud Pub/Sub
- Firestore for state management

**Error Handling**:
- Retry logic with exponential backoff
- Dead letter queue for failed messages
- Alerting via Cloud Monitoring

### 2. Content Processor Function

**Purpose**: Processes individual story URLs to extract article content

**Trigger**: Pub/Sub message from HN API Fetcher

**Concurrency**: Up to 20 parallel executions

**Flow**:
```
Pub/Sub → Content Processor → Script Generator (via Pub/Sub)
```

**Technologies**:
- Google Cloud Functions (2nd gen)
- BeautifulSoup4 for HTML parsing
- Goose3 as fallback extraction library
- Cloud Firestore for caching

**Error Handling**:
- Multiple extraction strategies (BeautifulSoup → Goose3 → Readability)
- Content validation and quality checks
- Timeout protection (30 seconds max)

### 3. Script Generator Function

**Purpose**: Generates podcast scripts using NotebookLM automation

**Trigger**: Pub/Sub message from Content Processor

**Flow**:
```
Pub/Sub → Script Generator → Audio Generator (via Pub/Sub)
```

**Technologies**:
- Google Cloud Functions (2nd gen) with extended memory
- Selenium WebDriver with Chrome headless
- Cloud Run for longer execution time (up to 60 minutes)

**Browser Automation Strategy**:
```python
# Pseudo-code for NotebookLM automation
def generate_script(article_content):
    driver = setup_chrome_driver()
    try:
        # Navigate to NotebookLM
        driver.get("https://notebooklm.google.com")

        # Create new notebook
        create_notebook_button = wait_for_element(driver, "create-notebook")
        create_notebook_button.click()

        # Upload content as source
        upload_source(driver, article_content)

        # Generate script with optimized prompt
        script = generate_with_prompt(driver, PODCAST_PROMPT)

        return clean_script(script)
    finally:
        driver.quit()
```

**Error Handling**:
- Selenium timeout protection
- UI element change detection
- Fallback to manual review queue

### 4. Audio Generator Function

**Purpose**: Converts text scripts to high-quality MP3 audio

**Trigger**: Pub/Sub message from Script Generator

**Flow**:
```
Pub/Sub → Audio Generator → Podcast Publisher (via Pub/Sub)
```

**Technologies**:
- Google Cloud Text-to-Speech API
- SSML for speech enhancement
- Cloud Storage for audio file hosting

**Audio Configuration**:
```python
# Optimized TTS settings
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    speaking_rate=1.0,
    pitch=0.0,
    volume_gain_db=0.0,
    sample_rate_hertz=24000,
    effects_profile_id=['telephony-class-application']
)

voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Neural2-J",  # Professional male voice
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)
```

### 5. Podcast Publisher Function

**Purpose**: Creates RSS feed and publishes completed podcast

**Trigger**: Pub/Sub message when all 20 audio files are ready

**Flow**:
```
Pub/Sub → Podcast Publisher → Cloud Storage (RSS + Audio)
```

**RSS Generation**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>HackerCast: The Top 20 Daily</title>
    <description>Daily audio summaries of top Hacker News stories</description>
    <itunes:image href="https://storage.googleapis.com/hackercast-audio/cover-art.jpg"/>
    <!-- Episode items generated dynamically -->
  </channel>
</rss>
```

## Data Architecture

### 1. Firestore Collections

**Stories Collection**:
```javascript
{
  "date": "2024-01-15",
  "stories": [
    {
      "id": "story_id",
      "rank": 1,
      "title": "Article Title",
      "url": "https://example.com/article",
      "score": 450,
      "status": "completed", // pending, processing, completed, failed
      "content": "extracted article text...",
      "script": "generated podcast script...",
      "audio_url": "gs://hackercast-audio/2024-01-15/001-story-title.mp3",
      "duration_seconds": 185,
      "created_at": "2024-01-15T05:00:00Z",
      "completed_at": "2024-01-15T05:15:00Z"
    }
  ],
  "status": "completed", // pending, processing, completed, failed
  "total_duration": 3600,
  "rss_published_at": "2024-01-15T05:30:00Z"
}
```

**Processing Logs Collection**:
```javascript
{
  "date": "2024-01-15",
  "story_id": "story_id",
  "function": "content_processor",
  "status": "success", // success, error, retry
  "execution_id": "uuid",
  "start_time": "2024-01-15T05:01:00Z",
  "end_time": "2024-01-15T05:01:15Z",
  "error_message": null,
  "retry_count": 0
}
```

### 2. Cloud Storage Structure

```
hackercast-audio/
├── rss/
│   └── podcast.xml
├── cover-art/
│   └── cover-art.jpg
├── 2024-01-15/
│   ├── 001-article-title.mp3
│   ├── 002-another-article.mp3
│   └── ...
└── 2024-01-16/
    ├── 001-latest-article.mp3
    └── ...
```

## Scalability Design

### Horizontal Scaling

1. **Function Concurrency**:
   - HN API Fetcher: 1 instance (sequential processing)
   - Content Processor: 20 instances (parallel processing)
   - Script Generator: 5 instances (resource-intensive)
   - Audio Generator: 10 instances (I/O bound)

2. **Resource Allocation**:
   - Memory: 512MB - 2GB based on function complexity
   - CPU: 1-2 vCPUs for compute-intensive tasks
   - Timeout: 60 seconds (functions) to 60 minutes (Cloud Run)

### Vertical Scaling

1. **Auto-scaling Triggers**:
   - CPU utilization > 70%
   - Memory utilization > 80%
   - Request latency > 30 seconds

2. **Resource Limits**:
   - Maximum concurrent executions: 100
   - Maximum memory: 8GB
   - Maximum execution time: 60 minutes (Cloud Run)

## Security Architecture

### 1. Authentication & Authorization

**Service Accounts**:
```yaml
# HN API Fetcher Service Account
hn-fetcher-sa@hackercast.iam.gserviceaccount.com:
  roles:
    - Cloud Functions Invoker
    - Pub/Sub Publisher
    - Firestore User

# Content Processor Service Account
content-processor-sa@hackercast.iam.gserviceaccount.com:
  roles:
    - Pub/Sub Subscriber
    - Firestore User
    - Storage Object Creator

# Script Generator Service Account
script-generator-sa@hackercast.iam.gserviceaccount.com:
  roles:
    - Cloud Run Invoker
    - Firestore User
    - Pub/Sub Publisher

# Audio Generator Service Account
audio-generator-sa@hackercast.iam.gserviceaccount.com:
  roles:
    - Text-to-Speech User
    - Storage Object Creator
    - Firestore User
```

### 2. Network Security

1. **VPC Configuration**:
   - Private Google Access enabled
   - Egress rules for external API access
   - Internal communication via private IPs

2. **API Security**:
   - API keys for external services
   - OAuth 2.0 for Google services
   - Rate limiting and quotas

### 3. Data Security

1. **Encryption**:
   - Data at rest: AES-256 encryption
   - Data in transit: TLS 1.3
   - Key management: Cloud KMS

2. **Data Privacy**:
   - No personal data collection
   - Content caching with TTL
   - Automatic data retention policies

## Monitoring & Observability

### 1. Metrics Collection

**Key Performance Indicators**:
```yaml
Business Metrics:
  - daily_podcast_completion_rate
  - average_processing_time
  - audio_quality_score
  - rss_feed_update_success

Technical Metrics:
  - function_execution_count
  - function_error_rate
  - function_duration_p99
  - storage_usage_bytes
  - api_quota_usage

Cost Metrics:
  - daily_cloud_function_cost
  - storage_cost_per_gb
  - text_to_speech_api_cost
  - total_daily_operational_cost
```

### 2. Alerting Strategy

**Critical Alerts** (PagerDuty):
- Daily podcast generation failure
- Function error rate > 5%
- Storage quota exceeded
- Cost anomaly detection

**Warning Alerts** (Email):
- Individual story processing failure
- High function latency (>30s)
- API quota usage > 80%

### 3. Logging Architecture

```python
# Structured logging format
{
  "timestamp": "2024-01-15T05:01:00Z",
  "severity": "INFO",
  "trace": "projects/hackercast/traces/abc123",
  "component": "content_processor",
  "story_id": "story_123",
  "execution_id": "exec_456",
  "message": "Article content extracted successfully",
  "metadata": {
    "url": "https://example.com/article",
    "content_length": 5420,
    "extraction_method": "beautifulsoup"
  }
}
```

## Disaster Recovery

### 1. Backup Strategy

**Data Backups**:
- Firestore: Automatic daily exports to Cloud Storage
- Audio files: Cross-region replication
- Configuration: Version-controlled in Git

**Recovery Objectives**:
- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 24 hours

### 2. Failure Scenarios

**Complete System Failure**:
1. Deploy infrastructure from IaC templates
2. Restore Firestore from latest backup
3. Republish RSS feed from storage
4. Resume daily operations

**Partial Component Failure**:
1. Dead letter queue processing
2. Manual intervention for stuck stories
3. Fallback content extraction methods

## Performance Optimization

### 1. Caching Strategy

**Multi-Level Caching**:
```python
# L1: In-memory cache (function instance)
# L2: Firestore cache (24-hour TTL)
# L3: External API cache (1-hour TTL)

@cached(ttl=3600)
def get_story_details(story_id):
    # Check Firestore cache first
    cached = get_from_firestore_cache(story_id)
    if cached and not expired(cached):
        return cached

    # Fetch from HN API
    story = fetch_from_hn_api(story_id)
    cache_in_firestore(story_id, story)
    return story
```

### 2. Content Processing Optimization

**Parallel Processing**:
```python
# Process multiple stories concurrently
async def process_stories(story_ids):
    tasks = []
    for story_id in story_ids:
        task = asyncio.create_task(process_single_story(story_id))
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 3. Audio Generation Optimization

**Batch Processing**:
- Combine multiple short scripts
- Use SSML for natural speech patterns
- Optimize audio encoding settings

## Cost Optimization

### 1. Resource Right-Sizing

**Function Memory Allocation**:
```yaml
HN API Fetcher: 256MB (lightweight HTTP calls)
Content Processor: 512MB (HTML parsing)
Script Generator: 2GB (browser automation)
Audio Generator: 1GB (TTS processing)
Podcast Publisher: 256MB (XML generation)
```

### 2. Usage-Based Scaling

**Scheduled Scaling**:
- Scale down non-critical functions during off-hours
- Use preemptible instances for batch processing
- Implement intelligent retry logic to reduce redundant calls

### 3. Cost Monitoring

**Budget Alerts**:
- Daily cost threshold: $10
- Monthly cost threshold: $300
- Automatic scaling limits to prevent runaway costs

## Phase Implementation Strategy

### Phase 1: Proof of Concept (Current)
**Duration**: 1-2 weeks
**Goal**: Validate core technologies and workflow

**Components**:
- Basic HN API integration
- Simple content scraping
- Manual NotebookLM interaction
- Basic TTS conversion
- Static RSS generation

**Success Criteria**:
- Generate one complete podcast episode
- Validate content quality
- Confirm technical feasibility

### Phase 2: Automation & MVP
**Duration**: 3-4 weeks
**Goal**: Build automated serverless pipeline

**Components**:
- Complete Cloud Functions deployment
- Browser automation for NotebookLM
- Automated RSS generation
- Basic monitoring and alerting
- Error handling and retries

**Success Criteria**:
- Daily automated podcast generation
- 95% success rate
- Basic error recovery

### Phase 3: Production & Scale
**Duration**: 2-3 weeks
**Goal**: Production-ready system with monitoring

**Components**:
- Comprehensive monitoring and alerting
- Advanced error handling
- Performance optimization
- Security hardening
- Documentation and runbooks

**Success Criteria**:
- 99% uptime
- Sub-30 minute generation time
- Comprehensive observability

## Technology Stack Summary

**Core Infrastructure**:
- Google Cloud Platform
- Terraform for Infrastructure as Code
- Cloud Functions (2nd gen) and Cloud Run
- Cloud Scheduler for orchestration

**Data Storage**:
- Cloud Firestore (NoSQL database)
- Cloud Storage (object storage)
- Cloud Pub/Sub (messaging)

**External Services**:
- Hacker News API
- NotebookLM (via browser automation)
- Google Cloud Text-to-Speech
- Various web scraping targets

**Development Tools**:
- Python 3.11+
- Selenium WebDriver
- BeautifulSoup4 and Goose3
- pytest for testing
- GitHub Actions for CI/CD

**Monitoring & Observability**:
- Google Cloud Monitoring
- Cloud Logging
- Error Reporting
- PagerDuty for critical alerts

This architecture provides a robust, scalable foundation for HackerCast that can grow from a simple PoC to a production-ready podcast generation system serving thousands of subscribers.