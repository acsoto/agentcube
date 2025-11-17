## What's Inside

- **main.py**: FastAPI web service with LangChain agent
- **requirements.txt**: Python dependencies
- **.env.example**: Example environment configuration

## Features

- LangChain agent with Calculator and Weather tools
- FastAPI REST endpoints
- Works with or without OpenAI API key (mock mode)
- Container-ready configuration
- Simple and easy to debug

## Documentation

For detailed testing procedures, scenarios, and troubleshooting, see [TESTING_GUIDE.md](./TESTING_GUIDE.md).

## Requirements

- Python 3.8+
- Docker or Podman
- AgentRun CLI (from the implementation branch)
- OpenAI API key (optional, for full functionality)

## Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /tools` - List available tools
- `POST /invoke` - Execute agent with a prompt

## Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (optional)

# Run locally
python main.py
```

Then visit http://localhost:8080
