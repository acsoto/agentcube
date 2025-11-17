# Getting Started with AgentRun CLI

## Overview

This tutorial provides a comprehensive introduction to **AgentRun CLI**, a developer tool for packaging, building, and deploying AI agents to AgentCube. You will learn the complete agent lifecycle from local development to cloud deployment through a practical, hands-on example.

### What You'll Build

A **Sentiment Analysis Agent** that:
- Analyzes text sentiment (positive, negative, neutral)
- Provides confidence scores and detailed analysis
- Exposes HTTP API endpoints for easy integration
- Demonstrates best practices for agent development

### Tutorial Details

| Information         | Details                                                                      |
|:--------------------|:-----------------------------------------------------------------------------|
| Tutorial type       | Practical/Hands-on                                                           |
| Agent type          | HTTP API Service                                                             |
| Framework           | Python HTTP Server                                                           |
| Language            | Python 3.8+                                                                  |
| Tutorial components | Local development, packaging, building, publishing, and invoking agents      |
| Tutorial vertical   | Cross-vertical                                                               |
| Example complexity  | Beginner-friendly                                                            |
| Tools used          | AgentRun CLI, Docker                                                         |

## Prerequisites

Before starting this tutorial, ensure you have:

- **Python 3.8+** installed
- **Docker** installed and running
- **Git** (for cloning the repository)
- Basic understanding of Python and HTTP APIs

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/volcano-sh/agentcube.git
   cd agentcube/cli-agentrun/01-getting-started-with-agentrun-cli
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install AgentRun CLI:**
   ```bash
   cd ..
   pip install -e .
   cd 01-getting-started-with-agentrun-cli
   ```

4. **Launch Jupyter Notebook:**
   ```bash
   jupyter notebook getting_started_with_agentrun_cli.ipynb
   ```

## Tutorial Structure

The tutorial notebook covers:

1. **Installation** - Setting up AgentRun CLI
2. **Local Development** - Creating and testing the agent locally
3. **Packaging** - Using `agentrun pack` to prepare the workspace
4. **Building** - Using `agentrun build` to create container images
5. **Publishing** - Using `agentrun publish` to deploy to AgentCube
6. **Status Check** - Using `agentrun status` to monitor the agent
7. **Invocation** - Using `agentrun invoke` to test the deployed agent
8. **Python SDK** - Programmatic access for automation

## Project Structure

```
01-getting-started-with-agentrun-cli/
├── README.md                                    # This file
├── getting_started_with_agentrun_cli.ipynb     # Main tutorial notebook
├── requirements.txt                             # Python dependencies
├── images/                                      # Architecture diagrams
└── agent/                                       # Example agent
    ├── main.py                                  # Agent implementation
    └── requirements.txt                         # Agent dependencies
```

## The Sentiment Analysis Agent

The example agent provides:

### Endpoints

- **`GET /health`** - Health check endpoint
- **`POST /analyze`** - Analyze sentiment of a single text
- **`POST /batch`** - Analyze sentiment of multiple texts
- **`POST /`** - AgentCube invocation endpoint

### Features

- Rule-based sentiment analysis
- Support for positive and negative word detection
- Intensifier handling ("very", "extremely", etc.)
- Sentiment scoring and confidence levels
- Batch processing capability

### Example Usage

```python
# Analyze a single text
POST /analyze
{
  "text": "This is an amazing product! I love it!"
}

# Response
{
  "sentiment": "positive",
  "score": 0.375,
  "confidence": 0.75,
  "positive_words_found": 2,
  "negative_words_found": 0
}
```

## AgentRun CLI Workflow

The complete workflow consists of five main stages:

```
┌─────────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐     ┌────────┐
│ Development │ --> │   Pack   │ --> │  Build  │ --> │ Publish │ --> │ Invoke │
│    Agent    │     │          │     │  Image  │     │   to    │     │ Agent  │
│    Code     │     │          │     │         │     │ AgentCube│    │        │
└─────────────┘     └──────────┘     └─────────┘     └─────────┘     └────────┘
```

### 1. Package with `agentrun pack`

Prepares your agent workspace:
- Validates project structure
- Creates `agent_metadata.yaml`
- Generates `Dockerfile`

```bash
agentrun pack -f agent \
    --agent-name "sentiment-agent" \
    --description "Sentiment analysis agent" \
    --language "python" \
    --entrypoint "python main.py" \
    --port 8080
```

### 2. Build with `agentrun build`

Creates a container image:
- Builds Docker image
- Tags the image
- Updates metadata with build info

```bash
agentrun build -f agent --verbose
```

### 3. Publish with `agentrun publish`

Deploys to AgentCube:
- Registers the agent
- Pushes image to registry
- Creates deployment endpoint

```bash
agentrun publish -f agent \
    --version "v1.0.0" \
    --image-url "docker.io/myorg/sentiment-agent"
```

### 4. Invoke with `agentrun invoke`

Tests the deployed agent:

```bash
agentrun invoke -f agent \
    --payload '{"text": "This is great!"}'
```

### 5. Check Status with `agentrun status`

Monitors the agent:

```bash
agentrun status -f agent
```

## Best Practices

### Agent Development

1. **Test locally first** - Validate your agent works before deploying
2. **Implement health checks** - Use `/health` endpoint for monitoring
3. **Return structured JSON** - Make responses easy to parse
4. **Handle errors gracefully** - Use proper HTTP status codes
5. **Add logging** - Enable debugging with detailed logs

### Configuration

1. **Use descriptive names** - Make agents easy to identify
2. **Provide clear descriptions** - Help users understand your agent
3. **Specify correct entrypoint** - Ensure proper agent startup
4. **Choose appropriate build mode** - Local for dev, cloud for production
5. **Use semantic versioning** - Track changes with proper versions

### Deployment

1. **Test containers locally** - Verify before publishing
2. **Use proper image naming** - Follow conventions (org/agent-name)
3. **Tag images with versions** - Enable easy rollback
4. **Keep images small** - Use slim base images
5. **Document dependencies** - Clear requirements.txt

## Command Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `agentrun pack` | Package agent workspace | `agentrun pack -f ./agent --agent-name my-agent` |
| `agentrun build` | Build container image | `agentrun build -f ./agent --verbose` |
| `agentrun publish` | Publish to AgentCube | `agentrun publish -f ./agent --version v1.0.0` |
| `agentrun invoke` | Test deployed agent | `agentrun invoke -f ./agent --payload '{"text": "test"}'` |
| `agentrun status` | Check agent status | `agentrun status -f ./agent` |

## Troubleshooting

### Docker Issues

**Problem**: "Docker is not available"
- **Solution**: Install Docker and ensure it's running
- **Alternative**: Use `--build-mode cloud` for cloud builds

### Metadata Issues

**Problem**: "Metadata file not found"
- **Solution**: Run `agentrun pack` first to generate metadata
- **Check**: You're in the correct workspace directory

### Port Conflicts

**Problem**: "Port 8080 is already in use"
- **Solution**: Stop other services using port 8080
- **Alternative**: Change the port in agent_metadata.yaml

### Build Failures

**Problem**: Docker build fails
- **Solution**: Check Dockerfile syntax and dependencies
- **Debug**: Use `--verbose` flag for detailed logs

## Next Steps

After completing this tutorial, you can:

1. **Enhance the sentiment agent** with ML models
2. **Add authentication** using custom headers
3. **Implement streaming responses** for long-running tasks
4. **Create multi-agent systems** with agent communication
5. **Integrate external APIs** and services
6. **Build custom agents** for your use cases
7. **Explore cloud build mode** for serverless deployment
8. **Set up monitoring** for production agents

## Additional Resources

- [AgentRun CLI Documentation](../README.md)
- [Quick Start Guide](../QUICKSTART.md)
- [Example Agents](../examples/)
- [AgentCube Main Project](https://github.com/volcano-sh/agentcube)
- [Issue Tracker](https://github.com/volcano-sh/agentcube/issues)

## Getting Help

If you encounter issues:

- Run commands with `--verbose` flag
- Check `agentrun <command> --help`
- Review the [troubleshooting guide](../QUICKSTART.md#troubleshooting)
- Open an issue on [GitHub](https://github.com/volcano-sh/agentcube/issues)

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) file for details.

---

**Happy agent building! 🚀**
