# LangChain Agent with MCP Server Integration

## Overview

This tutorial demonstrates how to build a distributed AI agent system using a microservices architecture:

- **MCP Server**: A Model Context Protocol server providing utility tools (calculator, file operations, datetime utilities)
- **LangChain Agent**: An intelligent agent that discovers and orchestrates MCP server tools
- **AgentRun CLI**: Used to deploy both components separately to local Kubernetes

This showcases modern best practices for building scalable, maintainable AI agent systems where tools and orchestration are separated into independent services.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                             │
│                         │                                   │
│                         ▼                                   │
│            ┌────────────────────────┐                       │
│            │  LangChain Agent       │                       │
│            │  (Port 8080)           │                       │
│            │                        │                       │
│            │  - Receives prompts    │                       │
│            │  - Orchestrates tools  │                       │
│            │  - Returns responses   │                       │
│            └────────────┬───────────┘                       │
│                         │                                   │
│                         │ HTTP/MCP Protocol                 │
│                         ▼                                   │
│            ┌────────────────────────┐                       │
│            │  MCP Server            │                       │
│            │  (Port 8000)           │                       │
│            │                        │                       │
│            │  Tools:                │                       │
│            │  - Calculator          │                       │
│            │  - File Operations     │                       │
│            │  - DateTime Utils      │                       │
│            └────────────────────────┘                       │
│                                                              │
│         Both deployed separately to Kubernetes              │
└─────────────────────────────────────────────────────────────┘
```

## What You'll Learn

* **MCP Server Creation**: Build a server with multiple tool categories
* **LangChain Integration**: Connect LangChain agents to MCP servers
* **Microservices Architecture**: Deploy and manage distributed agent systems
* **Service Communication**: Enable inter-service communication in Kubernetes
* **Independent Scaling**: Scale tools and agents separately based on load

## Features

### MCP Server Tools (8 tools)

**Calculator Tools:**
- `calculate`: Evaluate mathematical expressions
- `power`: Calculate base^exponent

**File Operation Tools:**
- `write_file`: Write content to workspace files
- `read_file`: Read content from workspace files
- `list_files`: List all files in workspace

**DateTime Tools:**
- `get_current_time`: Get current date/time with timezone support
- `format_timestamp`: Convert Unix timestamps to formatted dates

**Info Tools:**
- `server_info`: Get MCP server information

### LangChain Agent Features

- **Automatic Tool Discovery**: Discovers all MCP server tools at startup
- **Tool Orchestration**: Uses LangChain's ReAct agent to decide which tools to use
- **Mock Mode**: Works without OpenAI API key for testing
- **Production Mode**: Uses OpenAI for real agent reasoning
- **Health Checks**: Provides health and status endpoints
- **Service Discovery**: Automatically connects to MCP server in Kubernetes

## Prerequisites

- **Python 3.8+**
- **Docker** (running)
- **Kubernetes** (Docker Desktop with K8s enabled, or minikube)
- **AgentRun CLI** installed
- Basic understanding of:
  - Python programming
  - REST APIs
  - LangChain agents (recommended)
  - MCP protocol basics (recommended)

## Quick Start

### 1. Install Dependencies

```bash
# Install AgentRun CLI
cd /path/to/agentcube/cmd/agentrun
pip install -e .

# Verify installation
kubectl agentrun --version
```

### 2. Deploy MCP Server

```bash
cd 03-langchain-agent-with-mcp-server

# Package MCP server
kubectl agentrun pack -f mcp_server \
    --agent-name "mcp-utility-server" \
    --language "python" \
    --entrypoint "python main.py" \
    --port 8000

# Build image
kubectl agentrun build -f mcp_server

# Deploy to Kubernetes
kubectl agentrun publish -f mcp_server \
    --version "v1.0.0" \
    --image-url "mcp-utility-server:latest" \
    --use-k8s
```

### 3. Deploy LangChain Agent

```bash
# Package agent
kubectl agentrun pack -f agent \
    --agent-name "langchain-mcp-agent" \
    --language "python" \
    --entrypoint "python main.py" \
    --port 8080

# Build image
kubectl agentrun build -f agent

# Deploy to Kubernetes
kubectl agentrun publish -f agent \
    --version "v1.0.0" \
    --image-url "langchain-mcp-agent:latest" \
    --use-k8s
```

### 4. Test the System

```bash
# Test with calculator
kubectl agentrun invoke -f agent \
    --payload '{"prompt": "Calculate 25 multiplied by 4"}' \
    --use-k8s

# Test with datetime
kubectl agentrun invoke -f agent \
    --payload '{"prompt": "What is the current time?"}' \
    --use-k8s

# Test with file operations
kubectl agentrun invoke -f agent \
    --payload '{"prompt": "Write Hello World to test.txt"}' \
    --use-k8s
```

## Detailed Tutorial

For a comprehensive, step-by-step guide with explanations, see the Jupyter notebook:

**📓 [langchain_agent_with_mcp_server.ipynb](./langchain_agent_with_mcp_server.ipynb)**

The notebook includes:
- Detailed explanations of each component
- Testing procedures for local and Kubernetes deployments
- Code walkthroughs and architecture discussions
- Troubleshooting tips and best practices
- Advanced usage scenarios

## Project Structure

```
03-langchain-agent-with-mcp-server/
├── README.md                                    # This file
├── requirements.txt                             # Tutorial dependencies
├── langchain_agent_with_mcp_server.ipynb       # Comprehensive tutorial notebook
│
├── mcp_server/                                  # MCP Server component
│   ├── main.py                                 # MCP server implementation
│   ├── requirements.txt                        # Server dependencies
│   ├── agent_metadata.yaml                     # Generated by agentrun pack
│   └── Dockerfile                              # Generated by agentrun pack
│
├── agent/                                       # LangChain Agent component
│   ├── main.py                                 # Agent implementation
│   ├── requirements.txt                        # Agent dependencies
│   ├── .env.example                            # Environment variable template
│   ├── agent_metadata.yaml                     # Generated by agentrun pack
│   └── Dockerfile                              # Generated by agentrun pack
│
└── images/                                      # Documentation images
    └── (architecture diagrams, if any)
```

## Configuration

### MCP Server Configuration

The MCP server runs on port 8000 and provides tools at the `/mcp` endpoint.

**Environment Variables:**
- None required (stateless server)

### Agent Configuration

The LangChain agent runs on port 8080 and connects to the MCP server.

**Environment Variables:**
- `MCP_SERVER_URL`: URL of the MCP server (default: `http://localhost:8000/mcp`)
- `OPENAI_API_KEY`: OpenAI API key for production mode (optional)
- `AGENT_PORT`: Port for the agent service (default: `8080`)

### Setting OpenAI API Key (Optional)

For production mode with real reasoning:

```bash
# Set environment variable in Kubernetes
kubectl set env deployment/langchain-mcp-agent \
    OPENAI_API_KEY=your-api-key-here \
    -n agentrun
```

## Testing

### Local Testing

**Test MCP Server:**
```bash
# Start server
cd mcp_server
python main.py

# In another terminal, test with MCP client
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from datetime import timedelta

async def test():
    async with streamablehttp_client('http://localhost:8000/mcp', {}, timedelta(seconds=30), False) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'Available tools: {len(tools.tools)}')

asyncio.run(test())
"
```

**Test LangChain Agent:**
```bash
# Start agent (make sure MCP server is running)
cd agent
export MCP_SERVER_URL=http://localhost:8000/mcp
python main.py

# Test with curl
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Calculate 10 + 5"}'
```

### Kubernetes Testing

```bash
# Check deployments
kubectl get pods -n agentrun
kubectl get services -n agentrun

# Check MCP server status
kubectl agentrun status -f mcp_server --use-k8s

# Check agent status
kubectl agentrun status -f agent --use-k8s

# Invoke agent
kubectl agentrun invoke -f agent \
    --payload '{"prompt": "test"}' \
    --use-k8s
```

## Scaling

### Scale MCP Server

```bash
kubectl scale deployment mcp-utility-server --replicas=3 -n agentrun
```

### Scale Agent

```bash
kubectl scale deployment langchain-mcp-agent --replicas=2 -n agentrun
```

## Troubleshooting

### MCP Server Not Accessible

**Problem**: Agent cannot connect to MCP server

**Solution**:
1. Check MCP server is running: `kubectl get pods -n agentrun`
2. Verify service exists: `kubectl get services -n agentrun`
3. Check agent logs: `kubectl logs deployment/langchain-mcp-agent -n agentrun`
4. Verify MCP_SERVER_URL is correct (should use Kubernetes service name)

### Agent Returns Mock Responses

**Problem**: Agent always returns mock responses

**Solution**:
- This is expected if OPENAI_API_KEY is not set
- The agent will still show available tools from MCP server
- To enable production mode, set OPENAI_API_KEY environment variable

### Tools Not Discovered

**Problem**: Agent shows 0 tools available

**Solution**:
1. Check MCP server is running and accessible
2. Verify MCP server endpoint returns tools: Test with MCP client
3. Check network connectivity between services
4. Restart agent deployment to re-discover tools

### Deployment Fails

**Problem**: `kubectl agentrun publish` fails

**Solution**:
1. Ensure Docker is running
2. Verify Kubernetes cluster is accessible: `kubectl cluster-info`
3. Check namespace exists: `kubectl get namespace agentrun`
4. Review build logs with `--verbose` flag

## Best Practices

### MCP Server
- Group related tools by functionality
- Use clear, descriptive tool names and descriptions
- Implement proper error handling
- Keep tools stateless when possible
- Log tool invocations for debugging

### LangChain Agent
- Cache tool discovery results
- Handle MCP server unavailability gracefully
- Implement retry logic for tool calls
- Use environment variables for configuration
- Add comprehensive logging

### Deployment
- Deploy services separately for independent scaling
- Use Kubernetes service discovery for inter-service communication
- Set appropriate resource limits
- Implement health checks
- Use secrets for sensitive data (API keys)

### Monitoring
- Track tool usage metrics
- Monitor agent response times
- Log MCP protocol communication
- Set up alerts for service failures

## Advanced Usage

### Adding Custom Tools

To add new tools to the MCP server:

1. Edit `mcp_server/main.py`
2. Add your tool function with `@mcp.tool()` decorator
3. Rebuild and redeploy:
   ```bash
   kubectl agentrun build -f mcp_server
   kubectl agentrun publish -f mcp_server --use-k8s
   ```
4. Restart agent to discover new tools:
   ```bash
   kubectl rollout restart deployment/langchain-mcp-agent -n agentrun
   ```

### Multiple MCP Servers

To connect one agent to multiple MCP servers:

1. Deploy multiple MCP servers with different tools
2. Modify agent to connect to multiple MCP URLs
3. Aggregate tools from all servers
4. Agent can now use tools from all servers

### Custom Agent Logic

To customize agent behavior:

1. Edit `agent/main.py`
2. Modify the agent prompt template
3. Adjust tool selection strategy
4. Add custom preprocessing/postprocessing
5. Rebuild and redeploy

## Cleanup

```bash
# Delete Kubernetes resources
kubectl delete deployment langchain-mcp-agent -n agentrun
kubectl delete deployment mcp-utility-server -n agentrun
kubectl delete service langchain-mcp-agent -n agentrun
kubectl delete service mcp-utility-server -n agentrun

# Remove Docker images
docker rmi langchain-mcp-agent:latest
docker rmi mcp-utility-server:latest

# Remove generated files
rm -f agent/agent_metadata.yaml agent/Dockerfile
rm -f mcp_server/agent_metadata.yaml mcp_server/Dockerfile
```

## Additional Resources

- **[MCP Protocol Specification](https://modelcontextprotocol.io/)** - Official MCP documentation
- **[LangChain Documentation](https://python.langchain.com/)** - LangChain framework docs
- **[AgentRun CLI Guide](../QUICKSTART.md)** - AgentRun CLI documentation
- **[FastMCP](https://github.com/modelcontextprotocol/fastmcp)** - FastMCP server framework
- **[AgentCube Project](https://github.com/volcano-sh/agentcube)** - Main AgentCube repository

## Tutorial Details

| Information         | Details                                                                      |
|:--------------------|:-----------------------------------------------------------------------------|
| Tutorial type       | Advanced Integration                                                         |
| Difficulty          | Intermediate                                                                 |
| Estimated time      | 45-60 minutes                                                                |
| Prerequisites       | Python, Docker, Kubernetes basics                                            |
| Technologies        | LangChain, MCP, FastAPI, Kubernetes                                          |
| Deployment target   | Local Kubernetes                                                             |

## Support

If you encounter issues or have questions:

1. Check the troubleshooting section above
2. Review the detailed Jupyter notebook tutorial
3. Check AgentRun CLI documentation: `kubectl agentrun --help`
4. Open an issue on [GitHub](https://github.com/volcano-sh/agentcube/issues)

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file in the main repository for details.

---

**Happy Building! 🚀**
