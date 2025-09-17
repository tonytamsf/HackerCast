# HackerCast API Specifications

## Overview

This document defines the detailed API contracts for all HackerCast components, including internal service communication, external API integrations, and data schemas.

## Internal API Contracts

### 1. HN API Fetcher Function

#### Trigger API

**Cloud Scheduler HTTP Trigger**:
```http
POST /fetch-top-stories
Content-Type: application/json
Authorization: Bearer <service-account-token>

{
  "trigger_time": "2024-01-15T05:00:00Z",
  "limit": 20
}
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "execution_id": "exec_20240115_050000",
  "timestamp": "2024-01-15T05:00:00Z",
  "stories_queued": 20,
  "status": "success",
  "message": "Successfully queued 20 stories for processing"
}
```

#### Pub/Sub Output Message

**Topic**: `story-content-requests`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "url": "https://example.com/article",
  "title": "Revolutionary AI Discovery",
  "score": 450,
  "timestamp": "2024-01-15T05:00:15Z",
  "retry_count": 0
}
```

### 2. Content Processor Function

#### Pub/Sub Input Message

**Subscription**: `story-content-requests-sub`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "url": "https://example.com/article",
  "title": "Revolutionary AI Discovery",
  "score": 450,
  "timestamp": "2024-01-15T05:00:15Z",
  "retry_count": 0
}
```

#### Processing API

**Function Signature**:
```python
def process_content(event: dict, context: object) -> dict:
    """
    Processes article content from URL.

    Args:
        event: Pub/Sub message containing story details
        context: Cloud Functions context object

    Returns:
        Processing result with extracted content

    Raises:
        ContentExtractionError: When content cannot be extracted
        ValidationError: When content doesn't meet quality thresholds
    """
```

**Internal Content Extraction API**:
```python
class ContentExtractor:
    def extract(self, url: str) -> ContentResult:
        """
        Extract content using multiple strategies.

        Returns:
            ContentResult with extracted text and metadata
        """

@dataclass
class ContentResult:
    text: str
    title: str
    author: Optional[str]
    published_date: Optional[datetime]
    word_count: int
    extraction_method: str  # "beautifulsoup", "goose3", "readability"
    quality_score: float    # 0.0 - 1.0
    is_valid: bool
```

#### Pub/Sub Output Message

**Topic**: `script-generation-requests`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "title": "Revolutionary AI Discovery",
  "url": "https://example.com/article",
  "content": {
    "text": "Full article text content...",
    "title": "Revolutionary AI Discovery",
    "author": "John Doe",
    "word_count": 1500,
    "extraction_method": "beautifulsoup",
    "quality_score": 0.85
  },
  "timestamp": "2024-01-15T05:01:30Z",
  "processing_time_ms": 2150
}
```

### 3. Script Generator Function

#### Pub/Sub Input Message

**Subscription**: `script-generation-requests-sub`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "title": "Revolutionary AI Discovery",
  "url": "https://example.com/article",
  "content": {
    "text": "Full article text content...",
    "title": "Revolutionary AI Discovery",
    "author": "John Doe",
    "word_count": 1500,
    "extraction_method": "beautifulsoup",
    "quality_score": 0.85
  },
  "timestamp": "2024-01-15T05:01:30Z"
}
```

#### NotebookLM Automation API

**Browser Automation Interface**:
```python
class NotebookLMAutomator:
    def create_notebook(self) -> str:
        """Create new notebook and return notebook ID."""

    def upload_source(self, notebook_id: str, content: str) -> str:
        """Upload content as source and return source ID."""

    def generate_script(self, notebook_id: str, prompt: str) -> str:
        """Generate script using prompt and return generated text."""

    def cleanup_notebook(self, notebook_id: str) -> None:
        """Clean up notebook resources."""

# Optimized prompt template
PODCAST_SCRIPT_PROMPT = """
Generate a conversational podcast script for this article that:

1. Opens with an engaging hook mentioning the article title
2. Summarizes the key points in 3-4 conversational sentences
3. Explains why this matters to the tech community
4. Concludes with a natural transition phrase

Requirements:
- Target duration: 60-90 seconds when spoken at normal pace
- Conversational tone, not formal
- No explicit transitions like "moving on" or "next"
- End with natural conclusion, not abrupt cutoff
- Focus on the "why it matters" not just "what happened"

Article: {content}
"""
```

#### Pub/Sub Output Message

**Topic**: `audio-generation-requests`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "title": "Revolutionary AI Discovery",
  "script": {
    "text": "Generated podcast script text...",
    "word_count": 120,
    "estimated_duration_seconds": 75,
    "quality_score": 0.92
  },
  "notebook_id": "nb_abc123",
  "timestamp": "2024-01-15T05:05:45Z",
  "generation_time_ms": 245000
}
```

### 4. Audio Generator Function

#### Pub/Sub Input Message

**Subscription**: `audio-generation-requests-sub`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "title": "Revolutionary AI Discovery",
  "script": {
    "text": "Generated podcast script text...",
    "word_count": 120,
    "estimated_duration_seconds": 75,
    "quality_score": 0.92
  },
  "timestamp": "2024-01-15T05:05:45Z"
}
```

#### Text-to-Speech API Integration

**Google Cloud TTS Configuration**:
```python
@dataclass
class TTSConfig:
    voice_name: str = "en-US-Neural2-J"
    language_code: str = "en-US"
    speaking_rate: float = 1.0
    pitch: float = 0.0
    volume_gain_db: float = 0.0
    sample_rate_hertz: int = 24000
    audio_encoding: str = "MP3"
    effects_profile: List[str] = field(default_factory=lambda: ["telephony-class-application"])

class AudioGenerator:
    def generate_audio(self, script: str, config: TTSConfig) -> AudioResult:
        """Generate audio from script using TTS API."""

@dataclass
class AudioResult:
    audio_content: bytes
    duration_seconds: float
    file_size_bytes: int
    sample_rate: int
    encoding: str
```

#### Cloud Storage Upload API

**Storage Interface**:
```python
class AudioStorage:
    def upload_audio(self,
                    audio_content: bytes,
                    story_id: str,
                    rank: int,
                    title: str,
                    date: str) -> str:
        """
        Upload audio file to Cloud Storage.

        Returns:
            Public URL of uploaded file
        """

    def get_file_path(self, story_id: str, rank: int, title: str, date: str) -> str:
        """Generate standardized file path."""
        # Format: YYYY-MM-DD/RRR-sanitized-title.mp3
        sanitized_title = self._sanitize_filename(title)
        return f"{date}/{rank:03d}-{sanitized_title}.mp3"
```

#### Pub/Sub Output Message

**Topic**: `podcast-publishing-updates`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "title": "Revolutionary AI Discovery",
  "audio": {
    "url": "https://storage.googleapis.com/hackercast-audio/2024-01-15/001-revolutionary-ai-discovery.mp3",
    "duration_seconds": 78,
    "file_size_bytes": 1250000,
    "encoding": "MP3"
  },
  "timestamp": "2024-01-15T05:08:20Z",
  "tts_time_ms": 3200
}
```

### 5. Podcast Publisher Function

#### Pub/Sub Input Message

**Subscription**: `podcast-publishing-updates-sub`

```json
{
  "execution_id": "exec_20240115_050000",
  "story_id": "39184562",
  "rank": 1,
  "title": "Revolutionary AI Discovery",
  "audio": {
    "url": "https://storage.googleapis.com/hackercast-audio/2024-01-15/001-revolutionary-ai-discovery.mp3",
    "duration_seconds": 78,
    "file_size_bytes": 1250000,
    "encoding": "MP3"
  },
  "timestamp": "2024-01-15T05:08:20Z"
}
```

#### RSS Generation API

**RSS Feed Structure**:
```python
@dataclass
class PodcastEpisode:
    title: str
    description: str
    pub_date: datetime
    duration: int  # seconds
    file_url: str
    file_size: int
    guid: str

@dataclass
class PodcastFeed:
    title: str = "HackerCast: The Top 20 Daily"
    description: str = "Daily audio summaries of top Hacker News stories"
    language: str = "en-us"
    copyright: str = "© 2024 HackerCast"
    webmaster: str = "podcast@hackercast.com"
    category: str = "Technology"
    image_url: str = "https://storage.googleapis.com/hackercast-audio/cover-art.jpg"
    episodes: List[PodcastEpisode] = field(default_factory=list)

class RSSGenerator:
    def generate_feed(self, episodes: List[PodcastEpisode]) -> str:
        """Generate RSS 2.0 XML feed."""

    def upload_feed(self, xml_content: str) -> str:
        """Upload RSS feed to public storage."""
```

## External API Integrations

### 1. Hacker News API

**Base URL**: `https://hacker-news.firebaseio.com/v0`

#### Get Top Stories

```http
GET /topstories.json
Accept: application/json

Response:
[39184562, 39183845, 39182901, ...]
```

#### Get Story Details

```http
GET /item/{story_id}.json
Accept: application/json

Response:
{
  "by": "author_username",
  "descendants": 25,
  "id": 39184562,
  "kids": [39184588, 39184612],
  "score": 450,
  "time": 1705305600,
  "title": "Revolutionary AI Discovery",
  "type": "story",
  "url": "https://example.com/article"
}
```

#### Error Handling

```python
class HNAPIClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_top_stories(self, limit: int = 20) -> List[int]:
        """Get top story IDs with retry logic."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_story(self, story_id: int) -> Optional[Dict]:
        """Get story details with retry logic."""
```

### 2. Google Cloud Text-to-Speech API

**Service**: `texttospeech.googleapis.com`

#### Synthesize Speech

```python
# Request format
request = texttospeech.SynthesizeSpeechRequest(
    input=texttospeech.SynthesisInput(text=script_text),
    voice=texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-J",
        ssml_gender=texttospeech.SsmlVoiceGender.MALE
    ),
    audio_config=texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0,
        pitch=0.0,
        volume_gain_db=0.0,
        sample_rate_hertz=24000,
        effects_profile_id=["telephony-class-application"]
    )
)

# Response format
response = client.synthesize_speech(request=request)
# response.audio_content contains the MP3 audio data
```

#### Error Handling

```python
class TTSClient:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def synthesize_speech(self, text: str, config: TTSConfig) -> bytes:
        """Synthesize speech with retry logic and quota management."""
        try:
            response = self.client.synthesize_speech(request=request)
            return response.audio_content
        except google.api_core.exceptions.QuotaExceeded:
            # Handle quota exceeded with exponential backoff
            raise
        except google.api_core.exceptions.InvalidArgument as e:
            # Handle invalid text input
            logger.error(f"Invalid TTS input: {e}")
            raise
```

## Data Schemas

### 1. Firestore Document Schemas

#### Stories Collection

```typescript
interface StoryDocument {
  // Document ID: YYYY-MM-DD
  date: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: Timestamp;
  updated_at: Timestamp;
  stories: StoryItem[];
  total_duration: number;
  rss_published_at?: Timestamp;
  error_message?: string;
}

interface StoryItem {
  id: string;              // HN story ID
  rank: number;            // 1-20
  title: string;
  url: string;
  score: number;
  status: "pending" | "content_extracted" | "script_generated" | "audio_generated" | "completed" | "failed";
  content?: ContentData;
  script?: ScriptData;
  audio?: AudioData;
  error_message?: string;
  created_at: Timestamp;
  completed_at?: Timestamp;
}

interface ContentData {
  text: string;
  word_count: number;
  extraction_method: string;
  quality_score: number;
  extracted_at: Timestamp;
}

interface ScriptData {
  text: string;
  word_count: number;
  estimated_duration: number;
  quality_score: number;
  notebook_id: string;
  generated_at: Timestamp;
}

interface AudioData {
  url: string;
  duration_seconds: number;
  file_size_bytes: number;
  encoding: string;
  generated_at: Timestamp;
}
```

#### Processing Logs Collection

```typescript
interface ProcessingLog {
  // Document ID: auto-generated
  execution_id: string;
  story_id: string;
  function_name: string;
  status: "started" | "success" | "error" | "retry";
  start_time: Timestamp;
  end_time?: Timestamp;
  duration_ms?: number;
  error_message?: string;
  error_code?: string;
  retry_count: number;
  metadata: Record<string, any>;
}
```

#### Configuration Collection

```typescript
interface Configuration {
  // Document ID: "global"
  podcast: {
    title: string;
    description: string;
    author: string;
    email: string;
    image_url: string;
    language: string;
    category: string;
  };
  tts: {
    voice_name: string;
    language_code: string;
    speaking_rate: number;
    pitch: number;
    volume_gain_db: number;
  };
  processing: {
    max_stories: number;
    content_quality_threshold: number;
    script_quality_threshold: number;
    max_retries: number;
    timeout_seconds: number;
  };
  updated_at: Timestamp;
}
```

### 2. Pub/Sub Message Schemas

#### Base Message Schema

```typescript
interface BaseMessage {
  execution_id: string;     // Unique execution identifier
  timestamp: string;        // ISO 8601 timestamp
  retry_count: number;      // Number of retries attempted
  trace_id?: string;        // Distributed tracing ID
}
```

#### Story Processing Messages

```typescript
interface StoryContentRequest extends BaseMessage {
  story_id: string;
  rank: number;
  url: string;
  title: string;
  score: number;
}

interface ScriptGenerationRequest extends BaseMessage {
  story_id: string;
  rank: number;
  title: string;
  url: string;
  content: ContentData;
  processing_time_ms: number;
}

interface AudioGenerationRequest extends BaseMessage {
  story_id: string;
  rank: number;
  title: string;
  script: ScriptData;
  generation_time_ms: number;
}

interface PodcastUpdateMessage extends BaseMessage {
  story_id: string;
  rank: number;
  title: string;
  audio: AudioData;
  tts_time_ms: number;
}
```

## Error Handling Specifications

### 1. Error Categories

```python
class HackerCastError(Exception):
    """Base exception for HackerCast errors."""

class ContentExtractionError(HackerCastError):
    """Raised when content cannot be extracted from URL."""

class ScriptGenerationError(HackerCastError):
    """Raised when script generation fails."""

class AudioGenerationError(HackerCastError):
    """Raised when TTS conversion fails."""

class PublishingError(HackerCastError):
    """Raised when podcast publishing fails."""

class ValidationError(HackerCastError):
    """Raised when data validation fails."""
```

### 2. Retry Strategies

```python
# Exponential backoff with jitter
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10) + wait_random(0, 2),
    retry=retry_if_exception_type((requests.RequestException, TimeoutError)),
    before_sleep=before_sleep_log(logger, log_level=logging.WARNING)
)
def resilient_http_call(url: str) -> requests.Response:
    """HTTP call with retry logic."""

# Dead letter queue for permanent failures
def handle_permanent_failure(message: dict, error: Exception):
    """Send message to dead letter queue for manual review."""
    dlq_message = {
        "original_message": message,
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": datetime.utcnow().isoformat(),
        "requires_manual_review": True
    }
    publish_to_dlq(dlq_message)
```

### 3. Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
```

## Rate Limiting and Quotas

### 1. API Rate Limits

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    async def acquire(self):
        """Acquire rate limit token."""
        now = time.time()
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]

        if len(self.requests) >= self.requests_per_minute:
            wait_time = 60 - (now - self.requests[0])
            await asyncio.sleep(wait_time)

        self.requests.append(now)

# Usage
hn_rate_limiter = RateLimiter(requests_per_minute=60)
tts_rate_limiter = RateLimiter(requests_per_minute=300)
```

### 2. Quota Management

```python
class QuotaManager:
    def __init__(self):
        self.daily_quotas = {
            "tts_characters": 1000000,      # 1M characters/day
            "function_invocations": 10000,   # 10K invocations/day
            "storage_operations": 50000      # 50K operations/day
        }
        self.current_usage = {}

    def check_quota(self, service: str, amount: int) -> bool:
        """Check if quota allows the operation."""
        current = self.current_usage.get(service, 0)
        limit = self.daily_quotas.get(service, 0)
        return current + amount <= limit

    def consume_quota(self, service: str, amount: int):
        """Consume quota for operation."""
        self.current_usage[service] = self.current_usage.get(service, 0) + amount
```

This comprehensive API specification provides the foundation for implementing all HackerCast components with consistent interfaces, robust error handling, and scalable communication patterns.