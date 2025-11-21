# Building and Deploying AI Agents with AgentRun CLI

## Overview

In this tutorial, we will learn how to build, package, and deploy AI agents using the AgentRun CLI. This comprehensive guide walks you through the complete agent development lifecycle, from creating your agent code to deploying it on AgentCube.

We will focus on a practical example: a conversational assistant agent with tool-calling capabilities, demonstrating real-world development patterns.

### Tutorial Details

| Information         | Details                                                                      |
|:--------------------|:-----------------------------------------------------------------------------|
| Tutorial type       | End-to-end Development Workflow                                              |
| Agent type          | Single HTTP-based Agent                                                      |
| Framework           | Python with HTTP server                                                      |
| Tutorial components | AgentRun CLI complete workflow: pack, build, publish, invoke, status         |
| Tutorial vertical   | Cross-vertical                                                               |
| Example complexity  | Intermediate                                                                 |
| Tool used           | AgentRun CLI                                                                 |

### Tutorial Architecture

In this tutorial, we will demonstrate the complete workflow for developing and deploying an AI agent using AgentRun CLI.

Our example agent is a conversational assistant with tool-calling capabilities including:
- **Weather Tool**: Get weather information for any city
- **Calculator Tool**: Perform mathematical calculations
- **Time Tool**: Get current time in different timezones

<div style="text-align:left">
    <img src="images/architecture.png" width="100%"/>
</div>

### Tutorial Key Features

* Complete AgentRun CLI workflow (pack, build, publish, invoke, status)
* Building HTTP-based agents with Python
* Agent packaging and containerization best practices
* Tool-calling patterns for AI agents
* Integration with AgentCube platform
* Local development and testing

## Prerequisites

To execute this tutorial you will need:

* Python 3.8+
* pip (Python package manager)
* Docker (for building container images)
* Git
* AgentRun CLI installed

## What You'll Learn

By completing this tutorial, you will learn:

1. **Agent Development**
   - How to structure an AI agent application
   - Implementing HTTP endpoints for agent invocation
   - Adding tool-calling capabilities to agents
   - Best practices for agent code organization

2. **AgentRun CLI Workflow**
   - Packaging agents with `agentrun pack`
   - Building container images with `agentrun build`
   - Publishing agents with `agentrun publish`
   - Invoking agents with `agentrun invoke`
   - Checking agent status with `agentrun status`

3. **Deployment Best Practices**
   - Metadata configuration management
   - Dockerfile generation and customization
   - Container image optimization
   - Agent versioning and updates

4. **Integration Patterns**
   - Integrating AgentRun CLI into development workflows
   - Using the Python SDK for programmatic access
   - CI/CD integration patterns

## Tutorial Structure

This tutorial includes:

- **README.md** (this file) - Tutorial overview and documentation
- **complete_workflow_tutorial.ipynb** - Interactive Jupyter notebook with step-by-step instructions
- **requirements.txt** - Python dependencies for running the tutorial
- **agent/** - Sample agent application code
  - **main.py** - Agent entrypoint and HTTP server
  - **tools.py** - Tool implementations (weather, calculator, time)
  - **requirements.txt** - Agent dependencies

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Open the notebook:**
   ```bash
   jupyter notebook complete_workflow_tutorial.ipynb
   ```

3. **Follow the tutorial:**
   Execute each cell in the notebook sequentially to learn the complete AgentRun CLI workflow.

## Tutorial Outline

The notebook covers the following sections:

1. **Introduction** - Overview of AgentRun CLI and the tutorial
2. **Setting Up Your Environment** - Installing and configuring AgentRun CLI
3. **Creating Your Agent** - Building the sample agent application
4. **Local Testing** - Running and testing the agent locally
5. **Packaging with agentrun pack** - Creating a standardized agent workspace
6. **Building with agentrun build** - Generating container images
7. **Publishing with agentrun publish** - Deploying to AgentCube
8. **Invoking with agentrun invoke** - Testing deployed agents
9. **Checking Status with agentrun status** - Monitoring agent health
10. **Advanced Topics** - CI/CD integration and best practices
11. **Cleanup** - Removing resources

## Sample Agent Overview

The sample agent in this tutorial demonstrates:

- **HTTP Server**: Built with Python's http.server module
- **Tool Calling**: Three integrated tools for common tasks
- **JSON API**: RESTful API design patterns
- **Error Handling**: Robust error handling and validation
- **Health Checks**: Health endpoint for monitoring
- **Logging**: Structured logging for debugging

### API Endpoints

The agent exposes the following endpoints:

- `GET /health` - Health check endpoint
- `POST /invoke` - Main agent invocation endpoint
- `POST /tools/weather` - Get weather information
- `POST /tools/calculator` - Perform calculations
- `POST /tools/time` - Get current time

## Additional Resources

- [AgentRun CLI Documentation](../README.md)
- [Quick Start Guide](../QUICKSTART.md)
- [AgentRun CLI Design](../AgentRun-CLI-Design.md)
- [AgentCube Documentation](https://github.com/volcano-sh/agentcube)

## Next Steps

After completing this tutorial, you can:

1. Modify the sample agent to add your own functionality
2. Create your own agents from scratch
3. Integrate AgentRun CLI into your CI/CD pipeline
4. Explore advanced AgentCube features
5. Deploy production-ready agents to AgentCube

## Support

If you encounter issues or have questions:

- Check the [Troubleshooting Guide](../QUICKSTART.md#troubleshooting)
- Review the [FAQ](../README.md#faq)
- Open an issue on [GitHub](https://github.com/volcano-sh/agentcube/issues)

## License

This tutorial and sample code are provided under the Apache License 2.0.
