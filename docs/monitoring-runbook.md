# HackerCast Monitoring & Operations Runbook

## Overview

This runbook provides comprehensive guidance for monitoring, troubleshooting, and maintaining the HackerCast system in production. It includes alerting procedures, common issues, debugging workflows, and operational procedures.

## System Health Overview

### Key Performance Indicators (KPIs)

#### Business Metrics
- **Daily Podcast Completion Rate**: Target 99.5%
- **Average Story Processing Time**: Target < 30 minutes
- **Audio Quality Score**: Target > 0.9
- **RSS Feed Availability**: Target 99.9% uptime

#### Technical Metrics
- **Function Success Rate**: Target > 99%
- **End-to-End Latency**: Target < 45 minutes
- **Error Rate**: Target < 1%
- **Storage Usage Growth**: Monitor daily

#### Cost Metrics
- **Daily Operational Cost**: Budget $15/day
- **Cost per Episode**: Target < $0.75
- **Storage Cost Growth**: Monitor monthly

### Health Check Endpoints

**Function Health Checks**:
```bash
# HN Fetcher health
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
     https://us-central1-hackercast-prod.cloudfunctions.net/hn-fetcher/health

# Content Processor health (via Pub/Sub test message)
gcloud pubsub topics publish story-content-requests \
    --message='{"test": true, "health_check": true}'
```

**System Dependencies**:
```bash
# Check HN API availability
curl -f https://hacker-news.firebaseio.com/v0/topstories.json

# Check Google Cloud services status
gcloud services list --enabled --filter="name:cloudfunctions.googleapis.com"
gcloud services list --enabled --filter="name:texttospeech.googleapis.com"
```

## Monitoring Dashboard

### 1. Cloud Monitoring Setup

**Custom Metrics Configuration**:
```yaml
# metrics.yaml - Custom metrics for HackerCast
custom_metrics:
  - name: "podcast_generation_success_rate"
    type: "GAUGE"
    description: "Percentage of successful daily podcast generations"
    labels:
      - "date"
      - "environment"

  - name: "story_processing_duration"
    type: "HISTOGRAM"
    description: "Time taken to process individual stories"
    labels:
      - "function_name"
      - "status"

  - name: "content_quality_score"
    type: "GAUGE"
    description: "Quality score of extracted content"
    labels:
      - "extraction_method"
      - "story_id"

  - name: "audio_generation_cost"
    type: "CUMULATIVE"
    description: "Cost of TTS API usage"
    labels:
      - "date"
      - "character_count"
```

**Monitoring Queries**:
```sql
-- Daily podcast completion rate
SELECT
  DATE(timestamp) as date,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) / COUNT(*) * 100 as completion_rate
FROM
  `hackercast-prod.logs.story_processing`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC

-- Function error rates
SELECT
  function_name,
  COUNT(CASE WHEN severity = 'ERROR' THEN 1 END) / COUNT(*) * 100 as error_rate
FROM
  `hackercast-prod.logs.cloud_functions`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY function_name

-- Average processing time by stage
SELECT
  stage,
  AVG(duration_ms) as avg_duration_ms,
  PERCENTILE_CONT(duration_ms, 0.95) OVER() as p95_duration_ms
FROM
  `hackercast-prod.logs.processing_times`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY stage
```

### 2. Alerting Configuration

**Critical Alerts** (PagerDuty/On-call):

```yaml
# alerting-policies.yaml
alerting_policies:
  - name: "Daily Podcast Generation Failed"
    condition: |
      fetch_project('hackercast-prod')
      | filter(resource.type='cloud_function')
      | filter(resource.labels.function_name='hn-fetcher')
      | filter(jsonPayload.status='failed')
      | group_by([], 1m)
      | condition_count() > 0
    notification_channels:
      - "pagerduty-critical"
    documentation:
      content: "Daily podcast generation has failed. See runbook section 'Daily Generation Failure'"

  - name: "Function Error Rate High"
    condition: |
      error_rate > 5% over 10 minutes
    severity: "CRITICAL"
    notification_channels:
      - "pagerduty-critical"
      - "slack-alerts"

  - name: "Storage Quota Exceeded"
    condition: |
      storage_usage > 90% of quota
    severity: "CRITICAL"
    notification_channels:
      - "pagerduty-critical"

  - name: "TTS API Cost Anomaly"
    condition: |
      daily_tts_cost > $50 OR hourly_tts_cost > $10
    severity: "CRITICAL"
    notification_channels:
      - "pagerduty-critical"
      - "email-finance"
```

**Warning Alerts** (Email/Slack):

```yaml
warning_alerts:
  - name: "Individual Story Processing Failed"
    condition: |
      story_processing_failures > 2 in 1 hour
    severity: "WARNING"
    notification_channels:
      - "slack-warnings"

  - name: "High Function Latency"
    condition: |
      function_duration_p95 > 30 seconds
    severity: "WARNING"

  - name: "Content Quality Score Low"
    condition: |
      avg_content_quality < 0.7 over 1 hour
    severity: "WARNING"

  - name: "RSS Feed Update Delayed"
    condition: |
      rss_last_updated > 2 hours ago
    severity: "WARNING"
```

## Troubleshooting Procedures

### 1. Daily Generation Failure

**Symptoms**:
- Podcast not published by expected time (6:00 AM UTC)
- Multiple function execution failures
- RSS feed not updated

**Diagnosis Steps**:

```bash
# 1. Check overall system status
gcloud logging read 'resource.type="cloud_function" AND
    timestamp>="2024-01-15T05:00:00Z" AND
    severity>=ERROR' --limit=50 --format=json

# 2. Check HN API Fetcher execution
gcloud functions logs read hn-fetcher --region=us-central1 --limit=20

# 3. Check Firestore for today's execution
gcloud firestore collections documents list stories --filter="__name__ CONTAINS '$(date +%Y-%m-%d)'"

# 4. Check Pub/Sub message backlogs
gcloud pubsub subscriptions describe story-content-requests-sub
gcloud pubsub subscriptions describe script-generation-requests-sub
```

**Common Causes & Solutions**:

1. **HN API Unavailable**:
   ```bash
   # Check HN API status
   curl -I https://hacker-news.firebaseio.com/v0/topstories.json

   # Manual recovery: Retry with exponential backoff
   gcloud scheduler jobs run daily-podcast-trigger --location=us-central1
   ```

2. **Function Timeout/Memory Issues**:
   ```bash
   # Check function metrics
   gcloud logging read 'resource.type="cloud_function" AND
       (jsonPayload.message:"timeout" OR jsonPayload.message:"memory")'

   # Temporary fix: Increase memory/timeout via console
   # Long-term: Update Terraform configuration
   ```

3. **NotebookLM Automation Failure**:
   ```bash
   # Check script generator logs
   gcloud run services logs read script-generator --region=us-central1

   # Common issues:
   # - UI changes in NotebookLM
   # - Authentication problems
   # - Rate limiting

   # Recovery: Manual script generation for failed stories
   python scripts/manual-script-generation.py --story-ids=123,456,789
   ```

### 2. Individual Story Processing Failures

**Diagnosis Workflow**:

```bash
# 1. Identify failed stories
python scripts/check-failed-stories.py --date=$(date +%Y-%m-%d)

# 2. Analyze failure patterns
gcloud logging read 'resource.type="cloud_function" AND
    jsonPayload.story_id="STORY_ID" AND
    timestamp>="2024-01-15T00:00:00Z"' --format=json

# 3. Check content extraction issues
python scripts/test-content-extraction.py --url="STORY_URL"

# 4. Manual recovery for individual stories
python scripts/reprocess-story.py --story-id=STORY_ID --stage=content_extraction
```

**Recovery Procedures**:

```python
# scripts/reprocess-story.py
#!/usr/bin/env python3

import argparse
import json
from google.cloud import pubsub_v1, firestore

def reprocess_story(story_id: str, stage: str):
    """Reprocess a failed story from a specific stage."""

    db = firestore.Client()
    publisher = pubsub_v1.PublisherClient()

    # Get story details from Firestore
    today = datetime.now().strftime("%Y-%m-%d")
    doc_ref = db.collection('stories').document(today)
    doc = doc_ref.get()

    if not doc.exists:
        print(f"No stories found for {today}")
        return

    stories = doc.to_dict().get('stories', [])
    story = next((s for s in stories if s['id'] == story_id), None)

    if not story:
        print(f"Story {story_id} not found")
        return

    # Prepare message based on stage
    if stage == "content_extraction":
        topic = "story-content-requests"
        message = {
            "story_id": story_id,
            "url": story['url'],
            "title": story['title'],
            "rank": story['rank'],
            "retry": True
        }
    elif stage == "script_generation":
        topic = "script-generation-requests"
        message = {
            "story_id": story_id,
            "content": story['content'],
            "retry": True
        }
    # ... other stages

    # Publish message
    topic_path = publisher.topic_path("hackercast-prod", topic)
    publisher.publish(topic_path, json.dumps(message).encode())

    print(f"Reprocessing {story_id} from {stage}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-id", required=True)
    parser.add_argument("--stage", required=True,
                       choices=["content_extraction", "script_generation", "audio_generation"])
    args = parser.parse_args()

    reprocess_story(args.story_id, args.stage)
```

### 3. Performance Issues

**High Latency Diagnosis**:

```bash
# 1. Check function execution times
gcloud logging read 'resource.type="cloud_function" AND
    jsonPayload.duration_ms>30000' --limit=20

# 2. Analyze bottlenecks by function
python scripts/analyze-performance.py --timeframe="24h"

# 3. Check concurrent execution limits
gcloud functions describe FUNCTION_NAME --region=us-central1 --format="value(serviceConfig.maxInstanceCount)"
```

**Memory/CPU Issues**:

```bash
# Check resource utilization
gcloud logging read 'resource.type="cloud_function" AND
    (jsonPayload.message:"memory" OR jsonPayload.message:"cpu")'

# Temporary scaling adjustments
gcloud functions deploy FUNCTION_NAME \
    --memory=1024MB \
    --timeout=300s \
    --max-instances=20
```

### 4. Cost Anomalies

**Investigation Steps**:

```bash
# 1. Check TTS API usage
gcloud logging read 'resource.type="cloud_function" AND
    jsonPayload.component="audio_generator" AND
    jsonPayload.tts_characters>10000'

# 2. Analyze storage costs
gsutil du -sh gs://hackercast-audio/*

# 3. Check function invocation counts
gcloud logging read 'resource.type="cloud_function"' \
    --format="value(jsonPayload.execution_id)" | sort | uniq -c | sort -nr

# 4. Review Cloud Functions pricing
python scripts/cost-analysis.py --services=functions,storage,tts
```

**Cost Control Measures**:

```python
# scripts/cost-controls.py
def implement_cost_controls():
    """Implement automatic cost control measures."""

    # 1. Set function concurrency limits
    for function in ['content-processor', 'audio-generator']:
        update_function_config(function, max_instances=10)

    # 2. Implement TTS character limits
    daily_char_limit = 500000  # 500K characters/day
    current_usage = get_daily_tts_usage()

    if current_usage > daily_char_limit * 0.8:
        send_alert("TTS usage approaching daily limit")

    if current_usage > daily_char_limit:
        disable_tts_processing()
        send_critical_alert("TTS daily limit exceeded - processing halted")

    # 3. Cleanup old storage files
    cleanup_old_audio_files(days_to_keep=90)
```

## Operational Procedures

### 1. Daily Health Checks

**Morning Checklist** (7:00 AM UTC):

```bash
#!/bin/bash
# scripts/daily-health-check.sh

echo "=== Daily HackerCast Health Check ==="
DATE=$(date +%Y-%m-%d)

# 1. Check if today's podcast was generated
RSS_URL="https://storage.googleapis.com/hackercast-audio/rss/podcast.xml"
LATEST_EPISODE=$(curl -s $RSS_URL | grep -o '<pubDate>[^<]*</pubDate>' | head -1)
echo "Latest episode: $LATEST_EPISODE"

# 2. Verify all 20 stories processed
STORY_COUNT=$(gcloud firestore collections documents list stories \
    --filter="__name__ CONTAINS '$DATE'" --format="value(data)" | \
    jq '.stories | length')
echo "Stories processed: $STORY_COUNT/20"

# 3. Check error rates
ERROR_COUNT=$(gcloud logging read "timestamp>=\"${DATE}T00:00:00Z\" AND severity>=ERROR" \
    --format="value(timestamp)" | wc -l)
echo "Errors in last 24h: $ERROR_COUNT"

# 4. Verify RSS feed accessibility
HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}" $RSS_URL)
echo "RSS feed status: $HTTP_STATUS"

# 5. Check storage usage
STORAGE_USAGE=$(gsutil du -sh gs://hackercast-audio | cut -f1)
echo "Storage usage: $STORAGE_USAGE"

# 6. Verify function health
for func in hn-fetcher content-processor audio-generator podcast-publisher; do
    STATUS=$(gcloud functions describe $func --region=us-central1 \
        --format="value(serviceConfig.availableMemory)" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✓ $func: healthy"
    else
        echo "✗ $func: issue detected"
    fi
done

echo "=== Health Check Complete ==="
```

### 2. Weekly Maintenance

**Weekly Tasks** (Sundays, 2:00 AM UTC):

```bash
#!/bin/bash
# scripts/weekly-maintenance.sh

echo "=== Weekly Maintenance Starting ==="

# 1. Cleanup old logs
gcloud logging sinks delete old-logs-cleanup --quiet 2>/dev/null || true
gcloud logging sinks create old-logs-cleanup storage.googleapis.com/hackercast-logs \
    --log-filter="timestamp < \"$(date -d '30 days ago' '+%Y-%m-%dT%H:%M:%SZ')\""

# 2. Update function dependencies
for func_dir in src/*/; do
    if [ -f "$func_dir/requirements.txt" ]; then
        echo "Checking $func_dir for dependency updates..."
        cd "$func_dir"
        pip list --outdated --format=json > outdated.json
        cd ../..
    fi
done

# 3. Backup Firestore data
gcloud firestore export gs://hackercast-backups/weekly/$(date +%Y-%m-%d) \
    --collection-ids=stories,processing-logs,configuration

# 4. Cost analysis
python scripts/weekly-cost-report.py

# 5. Performance analysis
python scripts/weekly-performance-report.py

# 6. Security scan
gcloud container images scan gcr.io/hackercast-prod/script-generator:latest

echo "=== Weekly Maintenance Complete ==="
```

### 3. Monthly Reviews

**Monthly Tasks**:

1. **Capacity Planning**:
   ```bash
   # Analyze growth trends
   python scripts/capacity-analysis.py --period=monthly

   # Review quotas
   gcloud compute project-info describe --format="table(quotas.metric,quotas.usage,quotas.limit)"
   ```

2. **Security Review**:
   ```bash
   # Check IAM permissions
   python scripts/security-audit.py

   # Review service account usage
   gcloud logging read 'protoPayload.authenticationInfo.principalEmail!=""' \
       --format="table(protoPayload.authenticationInfo.principalEmail)" | sort | uniq -c
   ```

3. **Cost Optimization**:
   ```bash
   # Detailed cost breakdown
   python scripts/monthly-cost-analysis.py

   # Identify optimization opportunities
   python scripts/cost-optimization-recommendations.py
   ```

## Emergency Procedures

### 1. Complete System Outage

**Immediate Response** (within 15 minutes):

1. **Assess Impact**:
   ```bash
   # Check all core services
   python scripts/system-status-check.py --comprehensive
   ```

2. **Implement Workarounds**:
   ```bash
   # Publish emergency message to RSS feed
   python scripts/emergency-message.py --message="Technical difficulties - podcast delayed"

   # Enable maintenance mode
   python scripts/maintenance-mode.py --enable
   ```

3. **Escalate**:
   - Notify development team
   - Create incident ticket
   - Begin systematic diagnosis

### 2. Data Loss Recovery

**Recovery Procedure**:

1. **Assess Data Loss Scope**:
   ```bash
   # Check Firestore backup availability
   gsutil ls gs://hackercast-backups/weekly/

   # Verify audio file integrity
   python scripts/verify-audio-files.py --date-range="7d"
   ```

2. **Restore from Backup**:
   ```bash
   # Restore Firestore data
   gcloud firestore import gs://hackercast-backups/weekly/LATEST

   # Regenerate missing audio files
   python scripts/regenerate-audio.py --date-range="7d"
   ```

### 3. Security Incident

**Incident Response**:

1. **Immediate Containment**:
   ```bash
   # Disable compromised service accounts
   gcloud iam service-accounts disable SERVICE_ACCOUNT_EMAIL

   # Revoke API keys
   gcloud services api-keys update KEY_ID --restrictions-clear
   ```

2. **Investigation**:
   ```bash
   # Audit logs analysis
   gcloud logging read 'protoPayload.methodName="SetIamPolicy" OR
       protoPayload.methodName="CreateServiceAccount"' \
       --format=json > security-audit.json
   ```

3. **Recovery**:
   ```bash
   # Rotate all credentials
   python scripts/rotate-credentials.py --all

   # Update security policies
   terraform apply -target=module.security
   ```

## Performance Tuning

### 1. Function Optimization

**Memory and CPU Tuning**:

```python
# scripts/performance-tuning.py
FUNCTION_CONFIGS = {
    'hn-fetcher': {
        'memory': '256MB',
        'timeout': '60s',
        'max_instances': 1
    },
    'content-processor': {
        'memory': '512MB',
        'timeout': '120s',
        'max_instances': 20
    },
    'script-generator': {
        'memory': '2GB',
        'timeout': '1800s',
        'max_instances': 5
    },
    'audio-generator': {
        'memory': '1GB',
        'timeout': '300s',
        'max_instances': 10
    }
}

def optimize_function_config(function_name: str):
    """Optimize function configuration based on historical performance."""

    # Analyze historical execution data
    performance_data = get_function_performance(function_name, days=30)

    # Calculate optimal memory
    p95_memory = performance_data['memory_usage_p95']
    optimal_memory = min(p95_memory * 1.2, 8192)  # 20% buffer, max 8GB

    # Calculate optimal timeout
    p95_duration = performance_data['duration_p95']
    optimal_timeout = min(p95_duration * 2, 3600)  # 2x buffer, max 1 hour

    # Update function configuration
    update_function(function_name, {
        'memory': f"{optimal_memory}MB",
        'timeout': f"{optimal_timeout}s"
    })
```

### 2. Concurrency Optimization

**Dynamic Scaling Configuration**:

```python
def optimize_concurrency():
    """Optimize function concurrency based on load patterns."""

    # Analyze daily load patterns
    load_data = get_daily_load_patterns(days=30)

    # Peak processing time: 5:00-6:00 AM UTC
    peak_instances = {
        'content-processor': 20,
        'script-generator': 8,
        'audio-generator': 15
    }

    # Off-peak processing
    normal_instances = {
        'content-processor': 5,
        'script-generator': 2,
        'audio-generator': 5
    }

    # Schedule scaling adjustments
    schedule_scaling_updates(peak_instances, normal_instances)
```

## Contact Information

### Escalation Contacts

**Primary On-Call**: +1-XXX-XXX-XXXX (PagerDuty)
**Secondary On-Call**: +1-XXX-XXX-XXXX (PagerDuty)
**Development Team Lead**: dev-lead@hackercast.com
**Infrastructure Team**: infra@hackercast.com
**Product Owner**: product@hackercast.com

### External Dependencies

**Google Cloud Support**: Case creation via Cloud Console
**NotebookLM Support**: Via Google AI support channels
**PagerDuty Support**: support@pagerduty.com

### Documentation Links

- [System Architecture](/docs/architecture.md)
- [API Specifications](/docs/api-specifications.md)
- [Deployment Guide](/docs/deployment-guide.md)
- [Development Workflow](/docs/development-workflow.md)
- [Incident Response Playbook](https://company.atlassian.net/wiki/incident-response)

This monitoring and operations runbook provides comprehensive guidance for maintaining HackerCast in production, ensuring high availability and quick resolution of any issues that arise.