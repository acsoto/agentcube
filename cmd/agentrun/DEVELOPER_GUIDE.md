# AgentRun CLI Developer Guide

AgentRun CLI is a command-line tool for packaging, building, and deploying AI agents to AgentCube. This guide provides comprehensive documentation for developers to understand, set up, and use the AgentRun CLI effectively.

---

## Table of Contents

- [Overview](#overview)
  - [What is AgentRun CLI?](#what-is-agentrun-cli)
  - [Key Features](#key-features)
  - [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Verify Installation](#verify-installation)
- [Quick Start Tutorial](#quick-start-tutorial)
  - [Step 1: Create Your Agent](#step-1-create-your-agent)
  - [Step 2: Package Your Agent](#step-2-package-your-agent)
  - [Step 3: Build the Container Image](#step-3-build-the-container-image)
  - [Step 4: Publish to AgentCube](#step-4-publish-to-agentcube)
  - [Step 5: Invoke Your Agent](#step-5-invoke-your-agent)
  - [Step 6: Check Agent Status](#step-6-check-agent-status)
- [Configuration](#configuration)
  - [Agent Metadata File](#agent-metadata-file)
  - [Metadata Field Reference](#metadata-field-reference)
  - [AgentCube Configuration](#agentcube-configuration)
- [Command Reference](#command-reference)
  - [pack](#pack)
  - [build](#build)
  - [publish](#publish)
  - [invoke](#invoke)
  - [status](#status)
- [Agent Development](#agent-development)
  - [Agent Structure](#agent-structure)
  - [HTTP API Contract](#http-api-contract)
  - [Health Check Endpoint](#health-check-endpoint)
  - [Using CodeInterpreterClient](#using-codeinterpreterclient)
- [Language Support](#language-support)
  - [Python Agents](#python-agents)
  - [Java Agents](#java-agents)
- [Programmatic SDK Usage](#programmatic-sdk-usage)
- [Troubleshooting](#troubleshooting)
  - [Common Issues and Solutions](#common-issues-and-solutions)
  - [Getting Help](#getting-help)
- [Examples](#examples)
  - [Hello Agent Example](#hello-agent-example)
  - [Math Agent Example](#math-agent-example)

---

## Overview

### What is AgentRun CLI?

AgentRun CLI is a developer tool that streamlines the development, packaging, building, and deployment of AI agents to AgentCube. It provides a unified interface for managing the complete agent lifecycle from local development to cloud deployment.

AgentCube is designed to extend Volcano's capabilities to natively support and manage AI Agent workloads, which are rapidly emerging in the fields of Generative AI and Large Language Model (LLM) applications.

### Key Features

- **Multi-language Support**: Python and Java (with more languages planned)
- **Flexible Build Modes**: Local Docker builds and cloud builds
- **AgentCube Integration**: Seamless publishing and management via AgentRuntime CRDs
- **Developer-friendly**: Rich CLI experience with detailed feedback and progress indicators
- **CI/CD Ready**: Python SDK for programmatic access
- **Session Management**: Automatic session ID tracking for stateful agent interactions
- **Auto-versioning**: Automatic semantic version incrementing on each build

### Architecture

AgentRun CLI follows a modular four-layer architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Layer                              │
│  Typer-based command interface with rich console output     │
├─────────────────────────────────────────────────────────────┤
│                    Runtime Layer                            │
│  Business logic: PackRuntime, BuildRuntime, PublishRuntime, │
│  InvokeRuntime, StatusRuntime                               │
├─────────────────────────────────────────────────────────────┤
│                   Operations Layer                          │
│  Core domain logic and orchestration                        │
├─────────────────────────────────────────────────────────────┤
│                    Services Layer                           │
│  External integrations: DockerService, MetadataService,     │
│  AgentCubeProvider                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Prerequisites

Before you start, make sure you have:

- **Python 3.8+** installed
- **Git** installed
- **Docker** installed and running (for local builds)
- **Kubernetes cluster** with AgentCube CRDs installed (for deployment)
- **kubectl** configured to access your cluster

### Installation

#### From PyPI (Recommended)

```bash
pip install agentrun-cli
```

#### From Source

```bash
# Clone the repository
git clone https://github.com/volcano-sh/agentcube.git
cd agentcube/cmd/agentrun

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

> **Note**
> On Microsoft Windows, use: `venv\Scripts\activate`

### Verify Installation

Verify that AgentRun CLI is installed correctly:

```bash
kubectl agentrun --help
```

You should see the help output with available commands:

```
Usage: kubectl-agentrun [OPTIONS] COMMAND [ARGS]...

  AgentRun CLI - A developer tool for AI agent lifecycle management.

Options:
  --version   Show version and exit
  -v, --verbose  Enable verbose output
  --help      Show this message and exit.

Commands:
  build    Build the agent image based on the packaged workspace.
  invoke   Invoke a published agent via AgentCube.
  pack     Package the agent application into a standardized workspace.
  publish  Publish the agent image to AgentCube.
  status   Check the status of a published agent.
```

---

## Quick Start Tutorial

This tutorial walks you through deploying your first agent to AgentCube.

### Step 1: Create Your Agent

Create a project folder and the agent source file:

```bash
mkdir my-first-agent
cd my-first-agent
```

Create a file named `main.py`:

```python
#!/usr/bin/env python3
"""
My First Agent - A simple AI agent example.
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class AgentHandler(BaseHTTPRequestHandler):
    """HTTP handler for the agent."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._send_json_response({"status": "healthy"})
        else:
            self._send_json_response({
                "message": "Hello from My First Agent!",
                "endpoints": ["GET /health", "POST /"]
            })

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            prompt = data.get('prompt', 'Hello!')
            response = {"response": f"You said: {prompt}", "agent": "my-first-agent"}
            self._send_json_response(response)
        else:
            self._send_error(404, "Endpoint not found")

    def _send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_error(self, status_code, message):
        self._send_json_response({"error": message}, status_code)

    def log_message(self, format, *args):
        pass  # Suppress logging


def main():
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting agent on port {port}")
    server = HTTPServer(('', port), AgentHandler)
    server.serve_forever()


if __name__ == '__main__':
    main()
```

Create a `requirements.txt` file (can be empty for this basic example):

```
# Add your dependencies here
```

### Step 2: Package Your Agent

#### `kubectl agentrun pack`

Package the agent application into a standardized workspace.

| Option             | Description                                |
| ------------------ | ------------------------------------------ |
| `-f, --workspace`  | Path to the agent workspace directory.     |
| `--agent-name`     | Override the agent name.                   |
| `--language`       | Programming language (`python`, `java`).   |
| `--entrypoint`     | Override the entrypoint command.           |
| `--port`           | Port to expose in the Dockerfile.          |
| `--description`    | Agent description.                         |

Package your agent workspace:

```bash
kubectl agentrun pack
```
OR

```bash
kubectl agentrun pack -f . --agent-name "my-first-agent"
```

**Success:** You should see output similar to:

```
Successfully packaged agent: my-first-agent
Workspace: /path/to/my-first-agent
Metadata: /path/to/my-first-agent/agent_metadata.yaml
```

This command:
- Validates your workspace structure
- Creates or updates the `agent_metadata.yaml` configuration file
- Generates a `Dockerfile` for containerization

**Crucial Fields for Agentcube Deployment:**

*   `workload_manager_url`: The endpoint for the Agentcube Workload Manager.
*   `router_url`: The endpoint for the Agentcube Router.
*   `readiness_probe_path`: A health check endpoint on your agent (e.g., `/health`).
*   `readiness_probe_port`: The port for the health check endpoint.
*   `registry_url`: The URL of the container registry where your agent's image will be stored.

**Example `agent_metadata.yaml` for Agentcube:**
```yaml
agent_name: hello-agent
description: null
language: python
entrypoint: python main.py
port: 8080
build_mode: local
region: null
version: null
image: null
auth: null
requirements_file: requirements.txt
# --- Required for Agentcube ---
registry_url: "docker.io/your-username"
registry_username: "docker-login-username"
registry_password: "docker-login-credentials"
workload_manager_url: "http://workload-manager.agentcube-system.svc.cluster.local"
router_url: "http://router.agentcube-system.svc.cluster.local"
readiness_probe_path: "/health"
readiness_probe_port: 8080
# --- End Required ---
agent_endpoint: null
agent_id: null
session_id: null
k8s_deployment: null
```

### Step 3: Build the Container Image

#### `kubectl agentrun build`

Build the agent image based on the packaged workspace.

| Option             | Description                                |
| ------------------ | ------------------------------------------ |
| `-f, --workspace`  | Path to the agent workspace directory.     |
| `-p, --proxy`      | Custom proxy URL for dependency resolution.|
| `--cloud-provider` | Cloud provider name (e.g., huawei).        |
| `--output`         | Output path for build artifacts.           |
| `--verbose`        | Enable detailed logging.                   |

Build the Docker image:

```bash
kubectl agentrun build
```

**Success:** You should see output similar to:

```
Successfully built agent image: my-first-agent:0.0.1
Tag: 0.0.1
Size: 125.4MB
```

> **Note**
> The version is automatically incremented with each build (0.0.1 → 0.0.2 → 0.0.3, etc.)

### Step 4: Publish to AgentCube

#### `kubectl agentrun publish`

Publish the agent to Agentcube.

| Option               | Description                                           |
| -------------------- | ----------------------------------------------------- |
| `-f, --workspace`    | Path to the agent workspace directory.                |
| `--version`          | Semantic version string (e.g., v1.0.0).               |
| `--image-url`        | Image repository URL to push the image to.            |
| `--image-username`   | Username for the image repository.                    |
| `--image-password`   | Password for the image repository.                    |
| `--namespace`        | Kubernetes namespace for deployment.                  |

Before publishing, configure your agent metadata with AgentCube-specific settings. Edit `agent_metadata.yaml`:

```yaml
agent_name: my-first-agent
language: python
entrypoint: python main.py
port: 8080
build_mode: local

# AgentCube configuration
router_url: "http://your-agentcube-router:8080"
workload_manager_url: "http://your-workload-manager:8080"
agent_endpoint: "http://your-agent-endpoint:8080"
readiness_probe_path: "/health"
readiness_probe_port: 8080

# Registry configuration
registry_url: "docker.io/username"
registry_username: "docker-login-username"
registry_password: "docker-login-credentials"
```

Publish the agent:

```bash
kubectl agentrun publish
```

**Success:** You should see output similar to:

```
Successfully published agent: my-first-agent
Agent ID: my-first-agent
Endpoint: http://your-agent-endpoint:8080
Namespace: default
Status: deployed
```

### Step 5: Invoke Your Agent

#### `kubectl agentrun invoke`

Invoke a published agent via Agentcube.

| Option           | Description                                                        |
| ---------------- | ------------------------------------------------------------------ |
| `-f, --workspace`| Path to the agent workspace directory.                             |
| `--payload`      | JSON-formatted input passed to the agent.                          |
| `--header`       | Custom HTTP headers (e.g., 'Authorization: Bearer token').         |

Test your deployed agent:

```bash
kubectl agentrun invoke --payload '{"prompt": "Hello, World!"}'
```

**Success:** You should see a response from your agent:

```
Successfully invoked agent
Response: {"response": "You said: Hello, World!", "agent": "my-first-agent"}
```

### Step 6: Check Agent Status

### `kubectl agentrun status`

Check the status of a published agent.

| Option           | Description                            |
| ---------------- | -------------------------------------- |
| `-f, --workspace`| Path to the agent workspace directory. |

Check the status of your deployed agent:

```bash
kubectl agentrun status
```

This displays a table with agent information:

```
┌─────────────────────────────────────────────────────────────┐
│                       Agent Status                          │
├─────────────────┬───────────────────────────────────────────┤
│ Property        │ Value                                     │
├─────────────────┼───────────────────────────────────────────┤
│ Agent Name      │ my-first-agent                            │
│ Agent ID        │ my-first-agent                            │
│ Status          │ deployed                                  │
│ Version         │ 0.0.1                                     │
│ Language        │ python                                    │
│ Build Mode      │ local                                     │
│ Endpoint        │ http://your-agent-endpoint:8080           │
└─────────────────┴───────────────────────────────────────────┘
```

---

## Configuration

### Agent Metadata File

AgentRun uses an `agent_metadata.yaml` file to configure your agent. This file is automatically created when you run the `pack` command, but you can also create it manually.

**Example `agent_metadata.yaml`:**

```yaml
# Basic agent configuration
agent_name: my-agent
description: "My AI agent that does amazing things"
language: python
entrypoint: python main.py
port: 8080
build_mode: local

# Version (auto-incremented during build)
version: "0.0.1"

# Dependency configuration
requirements_file: requirements.txt

# Registry configuration (for pushing images)
registry_url: "docker.io/username"
registry_username: ""
registry_password: ""

# AgentCube system configuration
router_url: "http://agentcube-router:8080"
workload_manager_url: "http://workload-manager:8080"
agent_endpoint: "http://agent-endpoint:8080"
readiness_probe_path: "/health"
readiness_probe_port: 8080
```

### Metadata Field Reference

| Field | Type | Required | Default | Description                                  |
|-------|------|----------|---------|----------------------------------------------|
| `agent_name` | string | Yes | - | Unique name identifying the agent              |
| `description` | string | No | - | Human-readable summary of the agent's purpose  |
| `language` | string | Yes | `python` | Programming language (`python` or `java`) |
| `entrypoint` | string | Yes | - | Command to launch the agent                    |
| `port` | int | Yes | `8080` | Port exposed by the agent runtime                  |
| `build_mode` | string | Yes | `local` | Build strategy (`local` or `cloud`)      |
| `version` | string | No | `0.0.1` | Semantic version string                      |
| `requirements_file` | string | No | `requirements.txt` | Python dependency file  |
| `registry_url` | string | No | - | Registry URL for image publishing             |
| `registry_username` | string | No | - | Registry username                        |
| `registry_password` | string | No | - | Registry password                        |
| `router_url` | string | Yes* | - | URL for the AgentCube Router                  |
| `workload_manager_url` | string | Yes* | - | URL for the Workload Manager        |
| `agent_endpoint` | string | Yes* | - | Public endpoint URL for the agent         |
| `readiness_probe_path` | string | Yes* | - | HTTP path for readiness probe       |
| `readiness_probe_port` | int | Yes* | - | Port for readiness probe               |

*Required for AgentCube deployment

### AgentCube Configuration

For deploying to AgentCube, you must configure the following settings:

1. **Router URL**: The URL of the AgentCube router service that handles agent invocations
2. **Workload Manager URL**: The URL of the workload manager service
3. **Agent Endpoint**: The public endpoint where your agent will be accessible
4. **Readiness Probe**: Path and port for health checks

These can be set:
- In `agent_metadata.yaml`
- Via environment variables (`ROUTER_URL`, `WORKLOADMANAGER_URL`)

---

## Command Reference

### pack

Package the agent application into a standardized workspace.

```bash
kubectl agentrun pack [OPTIONS]
```

**Options:**

| Option | Type | Default | Description                                  |
|--------|------|---------|----------------------------------------------|
| `-f, --workspace` | PATH | `.` | Path to the agent workspace directory |
| `--agent-name` | TEXT | - | Override the agent name                    |
| `--language` | TEXT | - | Programming language (`python`, `java`)      |
| `--entrypoint` | TEXT | - | Override the entrypoint command            |
| `--port` | INT | - | Port to expose in the Dockerfile                  |
| `--build-mode` | TEXT | - | Build strategy: `local` or `cloud`         |
| `--description` | TEXT | - | Agent description                         |
| `--output` | TEXT | - | Output path for packaged workspace             |
| `--verbose` | FLAG | - | Enable detailed logging                       |

**Example:**

```bash
# Package current directory with default settings
kubectl agentrun pack -f .

# Package with custom agent name and port
kubectl agentrun pack -f ./my-agent --agent-name "custom-agent" --port 9000

# Package to a different output directory
kubectl agentrun pack -f ./my-agent --output ./packaged-agent
```

**What it does:**

1. Validates workspace structure
2. Creates or loads `agent_metadata.yaml`
3. Applies CLI option overrides
4. Validates language compatibility
5. Processes dependencies
6. Generates Dockerfile (if not present)
7. Updates metadata with pack information

### build

Build the agent image based on the packaged workspace.

```bash
kubectl agentrun build [OPTIONS]
```

**Options:**

| Option | Type | Default | Description                                  |
|--------|------|---------|----------------------------------------------|
| `-f, --workspace` | PATH | `.` | Path to the agent workspace directory |
| `-p, --proxy` | TEXT | - | Custom proxy URL for dependency resolution  |
| `--cloud-provider` | TEXT | - | Cloud provider name (e.g., `huawei`)   |
| `--output` | TEXT | - | Output path for build artifacts                |
| `--verbose` | FLAG | - | Enable detailed logging                       |

**Example:**

```bash
# Build with default settings
kubectl agentrun build -f .

# Build with proxy for dependency resolution
kubectl agentrun build -f . --proxy "http://proxy.example.com:8080"

# Build with verbose output
kubectl agentrun build -f . --verbose
```

**What it does:**

1. Validates build prerequisites (Dockerfile exists)
2. Loads metadata
3. Auto-increments version (0.0.1 → 0.0.2)
4. Builds Docker image using local Docker daemon
5. Updates metadata with build information

### publish

Publish the agent to AgentCube.

```bash
kubectl agentrun publish [OPTIONS]
```

**Options:**

| Option | Type | Default | Description                                           |
|--------|------|---------|-------------------------------------------------------|
| `-f, --workspace` | PATH | `.` | Path to the agent workspace directory          |
| `--version` | TEXT | - | Semantic version string (e.g., `v1.0.0`)               |
| `--image-url` | TEXT | - | Image repository URL (required for local build mode) |
| `--image-username` | TEXT | - | Username for image repository                   |
| `--image-password` | TEXT | - | Password for image repository                   |
| `--description` | TEXT | - | Agent description                                  |
| `--region` | TEXT | - | Deployment region                                       |
| `--provider` | TEXT | `agentcube` | Target provider for deployment              |
| `--namespace` | TEXT | `default` | Kubernetes namespace for deployment          |
| `--verbose` | FLAG | - | Enable detailed logging                                |

**Example:**

```bash
# Publish with image URL
kubectl agentrun publish -f . --image-url "docker.io/username/my-agent"

# Publish with registry credentials
kubectl agentrun publish -f . \
  --image-url "private-registry.com/my-agent" \
  --image-username "user" \
  --image-password "pass"

# Publish to specific namespace
kubectl agentrun publish -f . --namespace "production"
```

**What it does:**

1. Loads metadata and validates configuration
2. Prepares image for publishing (tags and pushes to registry)
3. Deploys AgentRuntime CR to Kubernetes cluster
4. Updates metadata with deployment information

### invoke

Invoke a published agent via AgentCube.

```bash
kubectl agentrun invoke [OPTIONS]
```

**Options:**

| Option | Type | Default | Description                                         |
|--------|------|---------|-----------------------------------------------------|
| `-f, --workspace` | PATH | `.` | Path to the agent workspace directory        |
| `--payload` | TEXT | `{}` | JSON-formatted input passed to the agent          |
| `--header` | TEXT | - | Custom HTTP headers (can be specified multiple times) |
| `--provider` | TEXT | `agentcube` | Target provider for invocation            |
| `--verbose` | FLAG | - | Enable detailed logging                              |

**Example:**

```bash
# Simple invocation
kubectl agentrun invoke -f . --payload '{"prompt": "Hello!"}'

# Invocation with custom headers
kubectl agentrun invoke -f . \
  --payload '{"prompt": "Hello!"}' \
  --header "Authorization: Bearer token123"

# Invocation with multiple headers
kubectl agentrun invoke -f . \
  --payload '{"query": "What is 2+2?"}' \
  --header "Authorization: Bearer token" \
  --header "X-Custom-Header: value"
```

**What it does:**

1. Loads metadata and validates agent is published
2. Constructs invocation URL based on deployment type
3. Sends HTTP POST request to agent endpoint
4. Handles session ID management (sends/receives `X-Agentcube-Session-Id` header)
5. Returns agent response

### status

Check the status of a published agent.

```bash
kubectl agentrun status [OPTIONS]
```

**Options:**

| Option | Type | Default | Description                                  |
|--------|------|---------|----------------------------------------------|
| `-f, --workspace` | PATH | `.` | Path to the agent workspace directory |
| `--provider` | TEXT | `agentcube` | Target provider for status check   |
| `--verbose` | FLAG | - | Enable detailed logging                       |

**Example:**

```bash
# Check status
kubectl agentrun status -f .

# Check status with verbose output
kubectl agentrun status -f . --verbose
```

**What it does:**

1. Loads metadata
2. Queries AgentCube for AgentRuntime CR status
3. Displays formatted status table with agent information

---

## Agent Development

### Agent Structure

A typical AgentRun workspace contains:

```
my-agent/
├── agent_metadata.yaml    # Agent configuration (auto-generated)
├── Dockerfile            # Container definition (auto-generated)
├── requirements.txt      # Python dependencies
├── main.py              # Agent entrypoint
└── src/                 # Additional source code (optional)
```

### HTTP API Contract

AgentCube agents must implement a specific HTTP API contract:

| Endpoint | Method | Description                                         |
|----------|--------|-----------------------------------------------------|
| `/health` | GET | Health check endpoint (returns `200 OK` when healthy) |
| `/` | POST | Main invocation endpoint (accepts JSON payload)            |

**Request Format:**

```json
{
  "prompt": "User input or query",
  // Additional fields as needed by your agent
}
```

**Response Format:**

```json
{
  "response": "Agent output",
  // Additional fields as needed
}
```

### Health Check Endpoint

Your agent **must** implement a health check endpoint. This is used by AgentCube for:
- Readiness probes during deployment
- Load balancer health checks
- Monitoring agent availability

**Example implementation:**

```python
def do_GET(self):
    if self.path == '/health':
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode())
```

### Using CodeInterpreterClient

AgentCube provides a `CodeInterpreterClient` for executing code in sandboxed environments:

```python
from agentcube import CodeInterpreterClient

# Initialize the client
ci_client = CodeInterpreterClient()

# Run Python code
result = ci_client.run_code("python", "print('Hello, World!')")

# Execute shell commands
output = ci_client.execute_command("echo 'Hello from shell!'")
```

The `CodeInterpreterClient`:
- Connects to AgentCube's code interpreter backend
- Provides sandboxed code execution
- Maintains session state for persistent variables
- Supports multiple languages (Python, shell)

---

## Language Support

### Python Agents

Python is fully supported with automatic dependency management and Dockerfile generation.

**Requirements:**
- Python 3.8+
- `requirements.txt` file for dependencies

**Auto-generated Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
```

**Best Practices:**
- Use `requirements.txt` for all dependencies
- Set `PORT` environment variable support for flexible port configuration
- Implement proper error handling and logging
- Use async/await for I/O-bound operations

### Java Agents

Java is supported with Maven-based builds and OpenJDK runtime.

**Requirements:**
- Java 17+
- `pom.xml` file for Maven dependencies

**Auto-generated Dockerfile:**

```dockerfile
FROM maven:3.9-openjdk-17-slim AS builder

WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn clean package -DskipTests

FROM openjdk:17-jre-slim
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8080

CMD ["java", "-jar", "app.jar"]
```

---

## Programmatic SDK Usage

AgentRun provides Python classes for programmatic access, useful for CI/CD pipelines:

```python
from agentrun import PackRuntime, BuildRuntime, PublishRuntime, InvokeRuntime
from pathlib import Path

workspace = Path("./my-agent")

# Package the agent
pack_runtime = PackRuntime(verbose=True)
pack_result = pack_runtime.pack(
    workspace,
    agent_name="my-agent",
    language="python"
)
print(f"Packaged: {pack_result['agent_name']}")

# Build the image
build_runtime = BuildRuntime(verbose=True)
build_result = build_runtime.build(workspace)
print(f"Built: {build_result['image_name']}:{build_result['image_tag']}")

# Publish to AgentCube
publish_runtime = PublishRuntime(verbose=True, provider="agentcube")
publish_result = publish_runtime.publish(
    workspace,
    image_url="docker.io/username/my-agent"
)
print(f"Published: {publish_result['agent_id']}")

# Invoke the agent
invoke_runtime = InvokeRuntime(verbose=True, provider="agentcube")
response = invoke_runtime.invoke(
    workspace,
    payload={"prompt": "Hello!"},
    headers={"Authorization": "Bearer token"}
)
print(f"Response: {response}")
```

---

## Troubleshooting

### Common Issues and Solutions

#### Docker is not available

**Symptom:** Error message "Docker is not available or not running"

**Solution:**
1. Install Docker if not installed
2. Start the Docker daemon: `sudo systemctl start docker`
3. Verify Docker is running: `docker ps`
4. Ensure your user has Docker permissions: `sudo usermod -aG docker $USER`

#### Metadata file not found

**Symptom:** Error message "Metadata file not found"

**Solution:**
1. Run `kubectl agentrun pack` first to generate the metadata file
2. Ensure you're in the correct workspace directory
3. Check that `agent_metadata.yaml` exists in the workspace

#### Agent not published yet

**Symptom:** Error message "Agent is not published yet"

**Solution:**
1. Run `kubectl agentrun publish` before trying to invoke
2. Check that the build completed successfully with `kubectl agentrun status`
3. Verify the AgentRuntime CR was created: `kubectl get agentruntimes`

#### Missing AgentCube configuration

**Symptom:** Error message about missing `router_url` or `workload_manager_url`

**Solution:**
1. Add required fields to `agent_metadata.yaml`:
   ```yaml
   router_url: "http://your-router:8080"
   workload_manager_url: "http://your-workload-manager:8080"
   agent_endpoint: "http://your-endpoint:8080"
   readiness_probe_path: "/health"
   readiness_probe_port: 8080
   ```
2. Or set environment variables: `ROUTER_URL`, `WORKLOADMANAGER_URL`

#### Could not connect to agent

**Symptom:** Error message "Could not connect to agent"

**Solution:**
1. Verify the agent is running: `kubectl agentrun status -f .`
2. Check the agent endpoint is correct in metadata
3. Verify network connectivity to the agent endpoint
4. Check agent logs for errors: `kubectl logs <pod-name>`

#### Invalid JSON payload

**Symptom:** Error message "Invalid JSON payload"

**Solution:**
1. Ensure payload is valid JSON
2. Use proper quoting in shell: `--payload '{"key": "value"}'`
3. Escape special characters if needed

#### Permission denied during image push

**Symptom:** Docker push fails with authentication error

**Solution:**
1. Provide registry credentials:
   ```bash
   kubectl agentrun publish -f . \
     --image-url "registry.example.com/my-agent" \
     --image-username "user" \
     --image-password "pass"
   ```
2. Or configure credentials in `agent_metadata.yaml`
3. Or login manually: `docker login registry.example.com`

### Getting Help

```bash
# General help
kubectl agentrun --help

# Command-specific help
kubectl agentrun pack --help
kubectl agentrun build --help
kubectl agentrun publish --help
kubectl agentrun invoke --help
kubectl agentrun status --help
```

Enable verbose logging for detailed output:

```bash
kubectl agentrun <command> --verbose
```

---

## Examples

### Hello Agent Example

A simple agent that responds to greetings in multiple languages.

**Location:** `examples/hello-agent/`

**Features:**
- Multi-language greetings (English, Spanish, French, Chinese, Japanese)
- CodeInterpreterClient integration
- Health check endpoint

**Usage:**

```bash
# Package and build
kubectl agentrun pack -f examples/hello-agent --agent-name "hello-agent"
kubectl agentrun build -f examples/hello-agent

# Test locally (before publish)
cd examples/hello-agent
python main.py &
curl -X POST http://localhost:8080/greet \
  -H "Content-Type: application/json" \
  -d '{"name": "Developer", "language": "es"}'
# Response: {"greeting": "¡Hola, Developer!", ...}
```

### Math Agent Example

An AI agent using LangChain and LangGraph for solving math problems.

**Location:** `examples/math-agent/`

**Features:**
- LangChain/LangGraph integration
- OpenAI-compatible LLM backend
- Sandboxed Python code execution via CodeInterpreterClient
- Persistent memory across conversations

**Configuration:**

Set environment variables:
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4"
```

**Usage:**

```bash
# Package and build
kubectl agentrun pack -f examples/math-agent --agent-name "math-agent"
kubectl agentrun build -f examples/math-agent

# Invoke with a math problem
kubectl agentrun invoke -f examples/math-agent \
  --payload '{"query": "Calculate the factorial of 10"}'
```

---

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](../../LICENSE) file for details.

## Links

- [AgentCube Main Project](https://github.com/volcano-sh/agentcube)
- [Volcano Scheduler](https://github.com/volcano-sh/volcano)
- [Issue Tracker](https://github.com/volcano-sh/agentcube/issues)