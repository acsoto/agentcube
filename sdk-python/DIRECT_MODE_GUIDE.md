# AgentCube Direct Mode Guide (Simplified Architecture)

This guide explains how to use the rearchitected AgentCube with direct, hardcoded token authentication between the Python SDK and PicoD. This mode bypasses the WorkloadManager and Router, suitable for simple, standalone deployments.

## Architecture Overview

*   **PicoD**: The Code Interpreter agent running inside a container. It now accepts direct HTTP requests authenticated via a static token.
*   **Python SDK**: A lightweight client that connects directly to PicoD's IP/URL.
*   **Authentication**: A hardcoded Bearer token (`agentcube-secret-token`) is used for all requests.

## 1. Running PicoD

### Build the Image
You can build the lightweight PicoD image using the provided Dockerfile:

```bash
docker build -f images/picod/Dockerfile -t light-picod:latest .
```

### Run the Container
Start the container, exposing the API port (default 8080):

```bash
docker run -d --name my-picod -p 8080:8080 light-picod:latest
```

The server will start immediately and listen for requests on port 8080.

*   **Default Port**: 8080
*   **Authentication Token**: `agentcube-secret-token` (Hardcoded in `pkg/picod/server.go`)

## 2. Using the Python SDK

### Installation
The SDK dependencies have been simplified (removed `cryptography` and `PyJWT`).

```bash
cd sdk-python
pip install .
```

### Basic Usage

Use the `CodeInterpreterClient` to connect directly to your running PicoD instance.

```python
from agentcube import CodeInterpreterClient

# 1. Initialize Client (Direct Connection)
# Replace with your PicoD URL (e.g., http://localhost:8080)
picod_url = "http://localhost:8080"

print(f"Connecting to PicoD at {picod_url}...")

with CodeInterpreterClient(picod_url=picod_url, verbose=True) as client:
    
    # 2. Execute Shell Commands
    print("--- Shell Command ---")
    output = client.execute_command("echo 'Hello from Direct Mode!'")
    print(output)

    # 3. Run Python Code
    print("\n--- Python Code ---")
    code = """
    import math
    print(f"The value of pi is {math.pi:.4f}")
    """
    output = client.run_code("python", code)
    print(output)

    # 4. File Operations
    print("\n--- File Write & Read ---")
    client.write_file("Content created via SDK", "demo.txt")
    content = client.execute_command("cat demo.txt")
    print(f"File content: {content}")
```

## 3. Running Tests

An End-to-End (E2E) test script is provided to verify the direct connection and functionality.

**Prerequisite**: You must have the `light-picod:latest` image built (see Section 1).

```bash
cd sdk-python
# Install test dependencies
pip install pytest requests

# Run the test
# This script automatically starts a 'light-picod:latest' container for testing
python3 tests/e2e_picod_test.py
```

## Security Note

**WARNING**: This mode uses a **hardcoded static token** (`agentcube-secret-token`). 
*   It is intended for development, testing, or trusted internal network environments only.
*   Do not expose the PicoD port to the public internet without additional security layers (e.g., VPN, mTLS, or a reverse proxy).
