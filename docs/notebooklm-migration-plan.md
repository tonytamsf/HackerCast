# NotebookLM API Migration Plan

## Overview

This document outlines the plan to migrate HackerCast from Google Cloud Text-to-Speech (TTS) to NotebookLM API for generating podcast-style audio content from Hacker News stories.

## Current State Analysis

### Existing TTS Implementation
- **Module**: `tts_converter.py`
- **Technology**: Google Cloud Text-to-Speech API
- **Output**: Robotic text-to-speech audio in MP3 format
- **Authentication**: Google Cloud service account credentials
- **Limitations**: Mechanical voice quality, no conversational format

### Pipeline Integration
- Stories fetched via `hn_api.py`
- Content scraped via `scraper.py`
- Text converted to audio via `tts_converter.py`
- Manual execution in current PoC phase

## Migration Plan

### Phase 1: Research and Analysis

#### 1.1 NotebookLM API Research
- **Objective**: Understand API capabilities and limitations
- **Tasks**:
  - Investigate available endpoints for notebook creation
  - Document authentication requirements
  - Analyze rate limits and usage quotas
  - Review audio generation capabilities and formats
  - Understand content synthesis features

#### 1.2 Current Workflow Analysis
- **Objective**: Map existing TTS integration points
- **Tasks**:
  - Review `tts_converter.py` implementation
  - Identify input/output formats and data flow
  - Document error handling mechanisms
  - Analyze performance characteristics

#### 1.3 Architecture Design
- **Objective**: Plan NotebookLM integration approach
- **Tasks**:
  - Design notebook creation and management workflow
  - Plan content upload and organization strategy
  - Define audio generation request/response handling
  - Specify error handling and retry mechanisms

### Phase 2: Implementation

#### 2.1 Core Integration Module
- **Objective**: Create NotebookLM API client
- **Deliverable**: `notebooklm_client.py`
- **Features**:
  - Authentication handling
  - Notebook creation and management
  - Content upload functionality
  - Audio generation requests

#### 2.2 Content Processing Pipeline
- **Objective**: Adapt scraped content for NotebookLM
- **Tasks**:
  - Format article content for optimal synthesis
  - Implement content chunking for large articles
  - Add metadata and context for better audio generation
  - Create content validation and preprocessing

#### 2.3 Audio Generation Handler
- **Objective**: Manage NotebookLM audio creation
- **Features**:
  - Submit content for podcast-style generation
  - Monitor generation status and progress
  - Handle asynchronous processing workflows
  - Implement timeout and retry logic

#### 2.4 Audio Download and Storage
- **Objective**: Retrieve and manage generated audio
- **Tasks**:
  - Download completed audio files
  - Convert formats if necessary (maintain MP3 output)
  - Implement local storage and organization
  - Add file validation and integrity checks

### Phase 3: Pipeline Integration

#### 3.1 Module Replacement
- **Objective**: Replace TTS with NotebookLM
- **Tasks**:
  - Update `main.py` to use NotebookLM client
  - Remove Google Cloud TTS dependencies
  - Modify configuration for NotebookLM credentials
  - Update error handling for new API responses

#### 3.2 Dependencies Update
- **Objective**: Manage package requirements
- **Tasks**:
  - Remove `google-cloud-texttospeech` from requirements.txt
  - Add NotebookLM API client dependencies
  - Update authentication configuration
  - Modify environment variable requirements

### Phase 4: Testing and Validation

#### 4.1 Unit Testing
- **Objective**: Validate individual components
- **Tasks**:
  - Test NotebookLM API client functions
  - Validate content processing and formatting
  - Test audio download and storage mechanisms
  - Verify error handling scenarios

#### 4.2 Integration Testing
- **Objective**: Validate end-to-end workflow
- **Tasks**:
  - Test complete pipeline from HN stories to audio
  - Validate audio quality and format consistency
  - Test handling of various content types and sizes
  - Verify performance under different load conditions

#### 4.3 Quality Assurance
- **Objective**: Ensure production readiness
- **Tasks**:
  - Compare audio quality with previous TTS output
  - Validate podcast-style conversational format
  - Test error recovery and graceful degradation
  - Document known limitations and workarounds

## Expected Benefits

### Audio Quality Improvements
- **Natural Conversation**: Podcast-style discussion format instead of robotic reading
- **Content Synthesis**: Intelligent analysis and synthesis of multiple articles
- **Engagement**: More engaging and listenable audio content

### Technical Advantages
- **Advanced Processing**: Leverages NotebookLM's content understanding capabilities
- **Scalability**: Designed for handling multiple documents and complex content
- **Innovation**: Positions HackerCast at the forefront of AI-powered podcast generation

## Risk Mitigation

### API Availability
- **Risk**: NotebookLM API limitations or changes
- **Mitigation**: Maintain fallback to TTS as backup option

### Performance Considerations
- **Risk**: Slower generation times compared to TTS
- **Mitigation**: Implement asynchronous processing and status monitoring

### Cost Management
- **Risk**: Potentially higher API costs
- **Mitigation**: Monitor usage and implement cost controls

## Implementation Timeline

### Week 1: Research and Design
- Complete NotebookLM API research
- Finalize architecture design
- Set up development environment

### Week 2-3: Core Implementation
- Develop NotebookLM client module
- Implement content processing pipeline
- Create audio generation handler

### Week 4: Integration and Testing
- Integrate with existing pipeline
- Complete unit and integration testing
- Performance optimization and tuning

### Week 5: Validation and Documentation
- Quality assurance testing
- Documentation updates
- Deployment preparation

## Success Criteria

1. **Functional**: Complete pipeline generates podcast-style audio from HN stories
2. **Quality**: Audio output demonstrates conversational format and natural flow
3. **Performance**: Generation time remains within acceptable limits for daily podcast creation
4. **Reliability**: System handles errors gracefully and provides consistent output
5. **Maintainability**: Code is well-documented and follows project conventions

## Next Steps

1. Begin NotebookLM API research and documentation review
2. Set up development environment with API access
3. Create proof-of-concept integration with single article
4. Validate audio quality and format compatibility
5. Proceed with full implementation according to timeline