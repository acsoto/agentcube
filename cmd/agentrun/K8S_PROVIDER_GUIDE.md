# Kubernetes Provider Guide for AgentRun CLI

This guide explains how to use the Kubernetes provider in AgentRun CLI to deploy and test agents on a local Kubernetes cluster.

## Overview

The Kubernetes (K8s) provider enables you to deploy built agent images to a local Kubernetes cluster for testing and development. This is useful when the AgentCube API is not yet ready or when you want to test your agents in a Kubernetes environment before publishing to production.

## Features

The K8s provider supports the following operations:

1. **Publish**: Deploy agent image to K8s cluster with a NodePort service
2. **Invoke**: Call the deployed agent via the exposed NodePort
3. **Status**: Check the deployment status, pod health, and service information

## Prerequisites

### 1. Install Kubernetes Python Client

```bash
# Install the kubernetes package
pip install kubernetes

# Or install with k8s extras
pip install -e ".[k8s]"
```

### 2. Set Up Local Kubernetes Cluster

You need a local Kubernetes cluster. Options include:

#### Using Docker Desktop (Recommended for Development)
- Enable Kubernetes in Docker Desktop settings
- Docker Desktop automatically configures kubectl

#### Using Minikube
```bash
# Install minikube
brew install minikube  # macOS
# or follow: https://minikube.sigs.k8s.io/docs/start/

# Start minikube
minikube start

# Configure kubectl to use minikube
kubectl config use-context minikube
```

#### Using Kind (Kubernetes in Docker)
```bash
# Install kind
brew install kind  # macOS
# or follow: https://kind.sigs.k8s.io/docs/user/quick-start/

# Create a cluster
kind create cluster --name agentrun
```

### 3. Verify Kubernetes Access

```bash
# Check cluster connection
kubectl cluster-info

# Verify you can list namespaces
kubectl get namespaces
```

## Usage

### Step 1: Pack and Build Your Agent

First, prepare your agent workspace:

```bash
# Pack the agent
agentrun pack -f ./my-agent

# Build the container image locally
agentrun build -f ./my-agent
```

**Important**: The image must be available in your local Docker registry or the Docker daemon that Kubernetes can access.

### Step 2: Publish to Kubernetes

Deploy your agent to the local Kubernetes cluster:

```bash
# Basic deployment
agentrun publish -f ./my-agent --use-k8s

# Specify a custom NodePort (30000-32767)
agentrun publish -f ./my-agent --use-k8s --node-port 31000

# Deploy with multiple replicas
agentrun publish -f ./my-agent --use-k8s --replicas 3

# Verbose output for debugging
agentrun publish -f ./my-agent --use-k8s --verbose
```

**Output Example**:
```
✅ Successfully published agent: my-agent
🆔 Agent ID: my-agent
🌐 Endpoint: http://localhost:31234
🔌 NodePort: 31234
📦 Namespace: agentrun
```

### Step 3: Check Agent Status

Verify your agent is running correctly:

```bash
# Check status
agentrun status -f ./my-agent --use-k8s
```

**Output Example**:
```
┌────────────────┬─────────────────────────────┐
│ Property       │ Value                       │
├────────────────┼─────────────────────────────┤
│ Agent Name     │ my-agent                    │
│ Agent ID       │ my-agent                    │
│ Status         │ ready                       │
│ Version        │ N/A                         │
│ Language       │ python                      │
│ Build Mode     │ local                       │
│ Endpoint       │ http://localhost:31234      │
│ Namespace      │ agentrun                    │
│ NodePort       │ 31234                       │
│ Replicas       │ 1/1                         │
│ Pods           │ my-agent-xxx: Running       │
└────────────────┴─────────────────────────────┘
```

### Step 4: Invoke Your Agent

Test your deployed agent:

```bash
# Invoke with a JSON payload
agentrun invoke -f ./my-agent --use-k8s --payload '{"message": "Hello!"}'

# With custom headers
agentrun invoke -f ./my-agent --use-k8s --payload '{"prompt": "test"}' --header "Authorization: Bearer token123"
```

**Note**: The invoke command automatically uses the endpoint stored in the agent metadata, so you don't need to specify the URL manually.

## Metadata Configuration

When you publish to Kubernetes, the `agent_metadata.yaml` file is updated with K8s-specific information:

```yaml
agent_name: my-agent
description: My test agent
language: python
entrypoint: python main.py
port: 8080
build_mode: local

# Populated after build
image:
  repository_url: my-agent:latest
  tag: latest

# Populated after K8s publish
agent_id: my-agent
agent_endpoint: http://localhost:31234
k8s_deployment:
  deployment_name: my-agent
  service_name: my-agent
  namespace: agentrun
  node_port: 31234
  container_port: 8080
  replicas: 1
  service_url: http://localhost:31234
```

## Advanced Configuration

### Custom Namespace

By default, agents are deployed to the `agentrun` namespace. To use a different namespace, you'll need to modify the code or set up the KubernetesProvider with a custom namespace.

### Image Pull Policy

The K8s provider uses `IfNotPresent` as the image pull policy, which means:
- Kubernetes will use local images if available
- This works well with locally built images from Docker

If you're using an external registry, ensure the image is tagged correctly.

### Port Configuration

The agent's port (defined in `agent_metadata.yaml`) is used for:
1. **Container Port**: The port your application listens on inside the container
2. **Service Port**: The port exposed by the Kubernetes Service
3. **NodePort**: Auto-assigned by Kubernetes (30000-32767) unless you specify one

## Troubleshooting

### Issue: "Failed to initialize K8s provider"

**Cause**: Kubernetes client cannot connect to the cluster.

**Solution**:
```bash
# Check kubectl configuration
kubectl config view
kubectl cluster-info

# Verify the context is correct
kubectl config current-context

# Test basic connectivity
kubectl get nodes
```

### Issue: Image not found in cluster

**Cause**: The Docker image is not available to Kubernetes.

**Solution**:

For **Docker Desktop**:
- Images built locally are automatically available
- Just run `docker build` in your workspace

For **Minikube**:
```bash
# Point your shell to minikube's docker daemon
eval $(minikube docker-env)

# Rebuild your image
agentrun build -f ./my-agent
```

For **Kind**:
```bash
# Load the image into kind cluster
kind load docker-image my-agent:latest --name agentrun
```

### Issue: Cannot access service at NodePort

**Cause**: NodePort is not accessible on localhost.

**Solution**:

For **Minikube**:
```bash
# Use minikube's IP instead of localhost
minikube ip

# Access via: http://<minikube-ip>:<node-port>
```

For **Kind**:
```bash
# You may need port forwarding
kubectl port-forward -n agentrun service/my-agent 8080:8080

# Access via: http://localhost:8080
```

### Issue: Pods are not ready

**Cause**: The container is crashing or not starting.

**Solution**:
```bash
# Check pod status
kubectl get pods -n agentrun

# View pod logs
kubectl logs -n agentrun <pod-name>

# Describe pod for events
kubectl describe pod -n agentrun <pod-name>

# Common issues:
# - Wrong entrypoint command
# - Missing dependencies
# - Port mismatch
# - Application crashes on startup
```

## Cleanup

To remove deployed agents from the cluster:

```bash
# Delete a specific deployment and service
kubectl delete deployment my-agent -n agentrun
kubectl delete service my-agent -n agentrun

# Or delete the entire namespace
kubectl delete namespace agentrun
```

## Integration with Existing Workflow

The K8s provider is designed to complement the existing AgentCube workflow:

1. **Development**: Use `--use-k8s` for local testing
2. **Staging**: Deploy to AgentCube staging environment
3. **Production**: Publish to AgentCube production

Example workflow:
```bash
# 1. Develop and test locally with K8s
agentrun pack -f ./my-agent
agentrun build -f ./my-agent
agentrun publish -f ./my-agent --use-k8s
agentrun invoke -f ./my-agent --use-k8s --payload '{"test": "data"}'

# 2. When ready, publish to AgentCube
agentrun publish -f ./my-agent --version v1.0.0 \
  --image-url docker.io/myorg/my-agent \
  --image-username myuser \
  --image-password mypass
```

## Limitations

1. **NodePort Range**: NodePorts are limited to 30000-32767 range
2. **Local Access Only**: NodePort services are designed for local/development access
3. **No TLS/HTTPS**: Services are exposed over HTTP (use Ingress for production)
4. **Single Cluster**: Provider connects to your current kubectl context
5. **No Auto-scaling**: Replicas are static (use HPA in production)

## Next Steps

- Review the [AgentRun CLI Design](AgentRun-CLI-Design.md) for full architecture details
- Check out the [examples](examples/) directory for sample agents
- Explore Kubernetes documentation for advanced deployment options

## Support

For issues or questions:
- Open an issue at: https://github.com/volcano-sh/agentcube/issues
- Check the AgentRun documentation
- Review Kubernetes troubleshooting guides
