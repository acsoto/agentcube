# Kubernetes Provider Implementation Summary

## Overview

This document summarizes the Kubernetes (K8s) provider implementation for the AgentRun CLI. The K8s provider enables local testing of the full CLI application by deploying agents to a local Kubernetes cluster instead of requiring the AgentCube API.

## What Was Implemented

### 1. Core K8s Provider Service
**File**: `cmd/agentrun/agentrun/services/k8s_provider.py`

A complete Kubernetes provider service that handles:
- **Deployment Creation**: Creates/updates Kubernetes Deployments for agent containers
- **Service Exposure**: Creates NodePort services to expose agents externally
- **Status Monitoring**: Checks deployment status, pod health, and service information
- **Agent Deletion**: Cleanup of deployments and services
- **Name Sanitization**: Ensures agent names are K8s DNS-1123 compliant

Key Features:
- Automatic namespace creation (`agentrun` namespace by default)
- Support for custom NodePort specification (30000-32767)
- Configurable replicas for horizontal scaling
- Environment variable support
- Wait-for-ready functionality with timeout
- Comprehensive error handling

### 2. Enhanced Runtime Layers

#### Publish Runtime (`publish_runtime.py`)
- Added `use_k8s` parameter to constructor
- New method `_publish_to_k8s()` for K8s deployments
- Automatic K8s provider initialization when needed
- Updates metadata with K8s deployment information

#### Invoke Runtime (`invoke_runtime.py`)
- Added `use_k8s` parameter to constructor
- Enhanced `get_agent_status()` to support K8s status checking
- New method `_get_k8s_status()` for querying K8s cluster
- Automatic detection of K8s deployments from metadata

### 3. CLI Enhancements
**File**: `cmd/agentrun/agentrun/cli/main.py`

Added K8s-specific flags to commands:

**publish command**:
- `--use-k8s`: Deploy to local K8s cluster
- `--node-port`: Specify custom NodePort (30000-32767)
- `--replicas`: Number of pod replicas

**invoke command**:
- `--use-k8s`: Invoke K8s-deployed agent

**status command**:
- `--use-k8s`: Check K8s deployment status
- Enhanced output table with K8s-specific fields (namespace, NodePort, replicas, pod status)

### 4. Metadata Service Update
**File**: `cmd/agentrun/agentrun/services/metadata_service.py`

Added `k8s_deployment` field to `AgentMetadata` model:
```python
k8s_deployment: Optional[Dict[str, Any]] = Field(None, description="Kubernetes deployment information")
```

This field stores:
- `deployment_name`: K8s deployment name
- `service_name`: K8s service name
- `namespace`: K8s namespace
- `node_port`: Exposed NodePort
- `container_port`: Container port
- `replicas`: Number of replicas
- `service_url`: Full service URL

### 5. Dependency Management
**File**: `cmd/agentrun/pyproject.toml`

Added optional K8s dependencies:
```toml
[project.optional-dependencies]
k8s = [
    "kubernetes>=28.0.0",
]
```

### 6. Documentation
Created comprehensive guides:
- **K8S_PROVIDER_GUIDE.md**: Complete user guide with examples, troubleshooting, and workflows
- **K8S_IMPLEMENTATION_SUMMARY.md**: This file - implementation details and testing instructions

## How It Works

### Architecture Flow

```
User Command (CLI)
    ↓
CLI Layer (main.py) - parses --use-k8s flag
    ↓
Runtime Layer (publish_runtime.py, invoke_runtime.py)
    ↓
Services Layer (k8s_provider.py)
    ↓
Kubernetes API (via kubernetes Python client)
    ↓
Local K8s Cluster
```

### Publish Flow

1. User runs: `agentrun publish -f ./my-agent --use-k8s`
2. CLI parses command and creates `PublishRuntime(use_k8s=True)`
3. PublishRuntime calls `_publish_to_k8s()`
4. K8s provider creates:
   - Deployment with agent container
   - NodePort Service exposing the agent
5. Waits for deployment to be ready
6. Updates `agent_metadata.yaml` with K8s deployment info
7. Returns endpoint URL and NodePort to user

### Invoke Flow

1. User runs: `agentrun invoke -f ./my-agent --use-k8s --payload '{"test": "data"}'`
2. InvokeRuntime reads endpoint from metadata
3. Sends HTTP POST to `http://localhost:<NodePort>`
4. Returns agent response to user

### Status Flow

1. User runs: `agentrun status -f ./my-agent --use-k8s`
2. InvokeRuntime calls `_get_k8s_status()`
3. K8s provider queries:
   - Deployment status
   - Pod status and health
   - Service configuration
4. Returns comprehensive status information
5. CLI displays in formatted table

## Testing Instructions

### Prerequisites You Need to Provide

1. **Local Kubernetes Cluster**
   - Docker Desktop with Kubernetes enabled (recommended)
   - OR Minikube
   - OR Kind
   - Verify with: `kubectl cluster-info`

2. **Python Environment**
   - Python 3.8 or higher
   - Install dependencies:
     ```bash
     cd cmd/agentrun
     pip install -e ".[k8s]"
     ```

3. **Sample Agent**
   - Use the existing `examples/hello-agent` or create your own
   - Must have `agent_metadata.yaml` file
   - Must have a valid Dockerfile (created by `pack` command)

### Complete Testing Workflow

```bash
# 1. Navigate to agentrun directory
cd cmd/agentrun

# 2. Install with K8s support
pip install -e ".[k8s]"

# 3. Verify Kubernetes access
kubectl cluster-info
kubectl get nodes

# 4. Pack the example agent
agentrun pack -f examples/hello-agent

# 5. Build the Docker image
agentrun build -f examples/hello-agent

# 6. Publish to K8s cluster
agentrun publish -f examples/hello-agent --use-k8s --verbose

# Expected output:
# ✅ Successfully published agent: hello-agent-test
# 🆔 Agent ID: hello-agent-test
# 🌐 Endpoint: http://localhost:XXXXX
# 🔌 NodePort: XXXXX
# 📦 Namespace: agentrun

# 7. Check deployment status
agentrun status -f examples/hello-agent --use-k8s

# Expected output: Table showing deployment details, pod status, etc.

# 8. Verify with kubectl
kubectl get deployments -n agentrun
kubectl get services -n agentrun
kubectl get pods -n agentrun

# 9. Invoke the agent
agentrun invoke -f examples/hello-agent --use-k8s --payload '{"message": "Hello World!"}'

# 10. Test with custom NodePort
agentrun publish -f examples/hello-agent --use-k8s --node-port 31000

# 11. Test with multiple replicas
agentrun publish -f examples/hello-agent --use-k8s --replicas 3
agentrun status -f examples/hello-agent --use-k8s
# Should show: Replicas: 3/3
```

### What to Look For During Testing

1. **Successful Deployment**
   - No errors during publish
   - NodePort assigned (30000-32767 range)
   - Deployment appears in `kubectl get deployments -n agentrun`

2. **Pod Health**
   - Status command shows pods in "Running" phase
   - Replicas show as "ready/desired" (e.g., "1/1" or "3/3")
   - `kubectl logs -n agentrun <pod-name>` shows application running

3. **Service Accessibility**
   - NodePort service created: `kubectl get svc -n agentrun`
   - Can access endpoint: `curl http://localhost:<NodePort>`
   - Invoke command successfully calls the agent

4. **Metadata Updates**
   - `examples/hello-agent/agent_metadata.yaml` contains `k8s_deployment` section
   - `agent_endpoint` points to localhost with correct NodePort
   - `agent_id` matches deployment name

### Common Issues You Might Encounter

1. **"Failed to initialize K8s provider"**
   - Check kubectl configuration
   - Ensure Kubernetes cluster is running
   - Verify kubeconfig is accessible

2. **"Image not found"**
   - For Docker Desktop: Image should be automatically available
   - For Minikube: Use `eval $(minikube docker-env)` before building
   - For Kind: Use `kind load docker-image <image-name>`

3. **"Cannot connect to service"**
   - For Minikube: Use `minikube ip` instead of localhost
   - For Kind: May need port forwarding: `kubectl port-forward -n agentrun service/<name> 8080:8080`

4. **Pods not starting**
   - Check logs: `kubectl logs -n agentrun <pod-name>`
   - Verify entrypoint command in agent_metadata.yaml
   - Ensure image was built correctly

### Cleanup After Testing

```bash
# Delete specific agent deployment
kubectl delete deployment hello-agent-test -n agentrun
kubectl delete service hello-agent-test -n agentrun

# Or delete entire namespace
kubectl delete namespace agentrun
```

## Key Differences from AgentCube Flow

| Aspect | AgentCube | K8s Provider |
|--------|-----------|--------------|
| **Deployment Target** | Remote AgentCube platform | Local K8s cluster |
| **Service Exposure** | AgentCube handles routing | NodePort service (30000-32767) |
| **Authentication** | AgentCube API credentials | kubectl context |
| **Image Registry** | Push to remote registry | Local Docker images |
| **Agent ID** | Generated by AgentCube | Sanitized agent name |
| **Endpoint** | AgentCube URL | http://localhost:<NodePort> |
| **Status Check** | AgentCube API | K8s API (pods, deployments) |

## Design Decisions

1. **NodePort Service Type**: Chosen for simplicity and local access. LoadBalancer would require cloud provider or MetalLB.

2. **Default Namespace**: `agentrun` namespace isolates test deployments from system workloads.

3. **Name Sanitization**: Converts agent names to K8s-compliant format (lowercase, alphanumeric + hyphens).

4. **IfNotPresent Pull Policy**: Works with locally built images without requiring a registry.

5. **Synchronous Deployment**: Waits for deployment to be ready before returning (120s timeout).

6. **Metadata Storage**: Stores complete K8s info in agent_metadata.yaml for subsequent commands.

## Future Enhancements

Potential improvements (not implemented):
- Support for Ingress resources (HTTPS, custom domains)
- ConfigMap/Secret management for agent configuration
- Persistent volume support for stateful agents
- Helm chart generation
- Multi-cluster support
- Auto-scaling (HPA) configuration
- Resource limits/requests configuration
- Health check probe customization

## Files Modified/Created

### Created:
- `cmd/agentrun/agentrun/services/k8s_provider.py` (580 lines)
- `cmd/agentrun/K8S_PROVIDER_GUIDE.md`
- `cmd/agentrun/K8S_IMPLEMENTATION_SUMMARY.md`

### Modified:
- `cmd/agentrun/agentrun/services/metadata_service.py` (added k8s_deployment field)
- `cmd/agentrun/agentrun/runtime/publish_runtime.py` (added K8s publish flow)
- `cmd/agentrun/agentrun/runtime/invoke_runtime.py` (added K8s status checking)
- `cmd/agentrun/agentrun/cli/main.py` (added --use-k8s flags)
- `cmd/agentrun/pyproject.toml` (added kubernetes dependency)

## Integration with Existing Design

The K8s provider follows the existing architectural layers:

1. **CLI Layer**: Added flags but maintained existing command structure
2. **Runtime Layer**: Extended publish/invoke runtimes with K8s support
3. **Services Layer**: Added new k8s_provider.py following the pattern of agentcube_service.py
4. **Metadata**: Extended metadata model to support K8s fields

The implementation is **backward compatible** - existing AgentCube workflow is unchanged, K8s is opt-in via `--use-k8s` flag.

## Conclusion

The K8s provider successfully implements a local testing workflow that mirrors the AgentCube deployment process. It allows full CLI demonstration without requiring external API dependencies, while maintaining compatibility with the designed architecture and future AgentCube integration.
