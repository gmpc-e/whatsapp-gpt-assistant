# WhatsApp GPT Assistant - Development Guide

## Quick Setup

### Automated Setup
Run the setup script to create a virtual environment and configure everything:

```bash
python setup_dev.py
```

### Manual Setup
1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio  # For testing
   ```

3. Configure environment:
   ```bash
   cp .env.template .env
   # Edit .env with your API keys and settings
   ```

## Configuration

### Required Environment Variables
- `OPENAI_API_KEY`: Your OpenAI API key
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `GOOGLE_CREDENTIALS_PATH`: Path to Google OAuth credentials JSON
- `GOOGLE_TOKEN_PATH`: Path to store Google OAuth tokens

### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Calendar API and Tasks API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials JSON file
6. Set `GOOGLE_CREDENTIALS_PATH` to the file path

### Twilio Setup
1. Create Twilio account and get WhatsApp sandbox
2. Configure webhook URL: `https://your-domain.com/whatsapp`
3. Set environment variables with your Twilio credentials

## Running the Application

### Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_enhanced_nlp.py

# Run comprehensive test suite
python run_tests.py

# Run with coverage
pytest --cov=app tests/

# Run integration tests only
pytest tests/test_integration_full.py -v
```

### Health Checks
- Health endpoint: `GET /health`
- Debug endpoint: `GET /debug`

## PyCharm Setup

1. Open the project directory in PyCharm
2. Set Python interpreter to `venv/bin/python`
3. Use the pre-configured run configurations:
   - "WhatsApp Assistant" - runs the main application
   - "Tests" - runs the test suite

## Manual Testing

### Using ngrok for Webhook Testing
```bash
# Install ngrok
# Run your app locally
uvicorn app.main:app --reload --port 8000

# In another terminal, expose local server
ngrok http 8000

# Use the ngrok URL as your Twilio webhook URL
```

### Test Messages
Try these enhanced messages in WhatsApp:

**Calendar Queries:**
- "Show me events next week" - Enhanced week view
- "Show me events next Sunday" - Specific day query
- "Show me events tomorrow" - Tomorrow's schedule
- "Give me free slots next week to go to the beach" - Free time analysis
- "Show me a summary of this week with statistics" - Comprehensive overview

**Task Management:**
- "Create task: Buy groceries on January 15th at 2pm, location supermarket, note: don't forget milk" - Full task creation
- "Show me open tasks" - Filter by status
- "Show me completed tasks" - Completed items only
- "Show me all my tasks" - Everything
- "Give me task statistics" - Task summary

**General:**
- "Hello" - General chat
- "Schedule lunch tomorrow at 1pm" - Event creation

## Architecture Overview

### Key Components
- **FastAPI App** (`app/main.py`) - Main webhook handler
- **Intent Router** (`app/connectors/openai_intent.py`) - AI-powered message classification
- **Enhanced NLP** (`app/connectors/enhanced_nlp.py`) - Advanced date/time parsing
- **Connectors** - External service integrations (Google, Twilio, OpenAI)
- **Services** - Business logic (confirmation store, scheduler)
- **Utils** - Shared utilities (validation, rate limiting, logging)

### Data Flow
1. WhatsApp message → Twilio → FastAPI webhook
2. Message validation and sanitization
3. Intent classification via OpenAI
4. Route to appropriate handler (events, tasks, Q&A)
5. Execute action via connectors
6. Return TwiML response to WhatsApp

## New Features Added

### Enhanced Natural Language Processing
- Better date/time parsing ("next Sunday", "next week")
- Free time slot detection
- Task status filtering (open, completed, all)
- Comprehensive summaries and statistics

### Improved Error Handling
- Rate limiting for OpenAI API calls
- Retry logic for external API failures
- Comprehensive input validation
- Performance monitoring

### Better Logging and Monitoring
- Structured logging with colors
- Performance metrics collection
- Health check endpoint with service status
- Configuration validation on startup

### Testing Infrastructure
- Comprehensive test suite with pytest
- End-to-end webhook tests
- Rate limiting tests
- NLP processing tests

## Troubleshooting

### Common Issues
1. **Import errors**: Make sure virtual environment is activated
2. **API failures**: Check your API keys in .env file
3. **Google OAuth**: Ensure credentials file exists and is valid
4. **Webhook not receiving**: Check ngrok URL and Twilio configuration

### Debug Mode
Set `DEBUG_LOG_PROMPTS=true` in .env to see detailed OpenAI interactions.

### Logs
Check application logs for detailed error information and performance metrics.
