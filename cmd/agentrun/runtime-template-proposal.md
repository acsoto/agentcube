---
title: Sandbox Template for Agent and CodeInterpreter Runtimes
authors:
- @hzxuzhonghu
reviewers:
- "@volcano-sh/agentcube-approvers"
- TBD
approvers:
- "@volcano-sh/agentcube-approvers"
- TBD
creation-date: 2025-11-27

---

## Declarative API for Agent and CodeInterpreter Runtimes

### Summary

This proposal outlines a design for introducing a declarative API to manage runtime specifically for Agent and CodeInterpreter runtimes in AgentCube. The goal is to enable users to define desired states for their sandboxes, allowing the system to automatically handle creation on the arrival of first invocation. The whole workflow out of the scope of this proposal. So we will focus on the declarative API design and about the whole system architecture, there will be another proposal.

### Motivation

#### Goals

- Provide a declarative API for developers to specify desired runtime states for Agent and CodeInterpreter sandboxes.
- Enable automatic sandbox creation upon first invocation based on the defined runtime templates.
- Ensure seamless integration with existing AgentCube components and workflows.

#### Non-Goals
- This proposal does not cover the entire workflow of sandbox lifecycle management, focusing solely on the declarative API design.
- It does not address `Function` runtimes.
- It does not include implementation details for the automatic creation mechanism triggered by first invocation.
- It does not cover the workflow details of the dataplane.

### Proposal

#### User Stories (Optional)

##### Story 1

As an agentic AI developer, I want a security‑isolated runtime for executing code derived from LLM‑generated code, so that potentially untrusted analysis code can run safely without impacting other tenants, control‑plane components, or production data.
I should be able to declare this isolated runtime as part of a sandbox template, without manually managing pods, images, or security settings each time I add or update a code‑interpreter‑capable agent.

##### Story 2

As an agentic AI developer, I want to deploy my agents on the serverless platform in a declarative manner, specifying runtime configurations such as resource limits, environment variables, and security contexts in a sandbox template, so that I can ensure consistent and repeatable deployments across different environments without manual intervention.

### Design Details

#### Why not we use existing SandboxTemplate?

There is a existing [`SandboxTemplate`](http://github.com/kubernetes-sigs/agent-sandbox/blob/main/extensions/api/v1alpha1/sandboxtemplate_types.go#L57) in the kubernetes-sigs/agent-sandbox project. However, it is designed to be a generic template for various sandbox types and may not cater specifically to the unique requirements of Agent and CodeInterpreter runtimes. 

- SandboxTemplate simply reuses pod template, making it hard to express multi-version runtimes. As it is common to have multiple versions of Agent or CodeInterpreter runtimes, a more specialized template is needed to manage these variations effectively.
- Different runtimes may have distinct configuration needs that are not adequately addressed by a generic pod template. Likely we need to support warmpool for code  interpreter runtime, but not for agent runtime. Because code interpreter needs very lower latency for cold start, while agent runtime can afford longer cold start time.

By introducing a dedicated runtime template, we can tailor the API to better suit the specific needs of these runtimes, such as specialized configuration options, lifecycle management, and integration points.

#### Agent Runtime CRD

```go

// AgentRuntime defines the desired state of an agent runtime environment.
type AgentRuntime struct {
	metav1.TypeMeta `json:",inline"`
	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty,omitzero" protobuf:"bytes,1,opt,name=metadata"`
	// Spec defines the desired state of the AgentRuntime.
	Spec AgentRuntimeSpec `json:"spec" protobuf:"bytes,2,opt,name=spec"`
	// Status represents the current state of the AgentRuntime.
	Status AgentRuntimeStatus `json:"status" protobuf:"bytes,3,opt,name=status"`
}


type AgentRuntimeSpec struct {
	// Ports is a list of ports that the agent runtime will expose.
	Ports []TargetPort

	// PodTemplate describes the template that will be used to create an agent sandbox.
	// +kubebuilder:validation:Required
	Template *SandboxTemplate `json:"podTemplate" protobuf:"bytes,1,opt,name=podTemplate"`

	// SessionTimeout describes the duration after which an inactive session will be terminated.
	// +kubebuilder:validation:Required
	// +kubebuilder:default="15m"
	SessionTimeout *metav1.Duration `json:"sessionTimeout,omitempty" protobuf:"bytes,2,opt,name=sessionTimeout"`

	// MaxSessionDuration describes the maximum duration for a session.
	// After this duration, the session will be terminated no matter active or inactive.
	// +kubebuilder:validation:Required
	// +kubebuilder:default="8h"
	MaxSessionDuration *metav1.Duration `json:"maxSessionDuration,omitempty" protobuf:"bytes,3,opt,name=maxSessionDuration"`
}

type ProtocolType string

const (
	ProtocolTypeHTTP  ProtocolType = "HTTP"
	ProtocolTypeHTTPS ProtocolType = "HTTPS"
)

type TargetPort struct {
	// PathPrefix is the path prefix to route to this port.
	// For example, if PathPrefix is "/api", requests to "/api/..." will be routed to this port.
	// +optional
	PathPrefix string `json:"pathPrefix,omitempty" protobuf:"bytes,4,opt,name=pathPrefix"`
	// Name is the name of the port.
	// +optional
	Name string `json:"name,omitempty" protobuf:"bytes,1,opt,name=name"`
	// Port is the port number.
	Port uint32 `json:"port" protobuf:"varint,2,opt,name=port"`
	// Protocol is the protocol of the port.
	// +kubebuilder:default=HTTP
	// +kubebuilder:validation:Enum=HTTP;HTTPS;
	Protocol ProtocolType `json:"protocol" protobuf:"bytes,3,opt,name=protocol"`
}

type AgentRuntimeStatus struct {
	// DefaultVersion specifies the default version of the agent runtime.
	// This is automatically set to the latest version.
	DefaultVersion string            `json:"defaultVersion"`
	Versions       map[string]string `json:"versions"`
}

type SandboxTemplate struct {
	// Map of string keys and values that can be used to organize and categorize
	// (scope and select) objects. May match selectors of replication controllers
	// and services.
	// More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/labels
	// +optional
	Labels map[string]string `json:"labels,omitempty" protobuf:"bytes,1,rep,name=labels"`

	// Annotations is an unstructured key value map stored with a resource that may be
	// set by external tools to store and retrieve arbitrary metadata. They are not
	// queryable and should be preserved when modifying objects.
	// More info: https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations
	// +optional
	Annotations map[string]string `json:"annotations,omitempty" protobuf:"bytes,2,rep,name=annotations"`
	// Spec is the Pod's spec
	// +kubebuilder:validation:Required
	Spec corev1.PodSpec `json:"spec" protobuf:"bytes,3,opt,name=spec"`
}
```

below is an example of how to define an `AgentRuntime` CRD for an agent runtime environment:
```yaml
apiVersion: runtime.agentcube.io/v1alpha1  # adjust to your actual group/version
kind: AgentRuntime
metadata:
  name: foo
  labels:
    app: code-foo
spec:
  # Ports exposed by the runtime; your router/proxy will use these.
  ports:
    - name: http
      port: 8080
      protocol: HTTP
      pathPrefix: /api
    - name: metrics
      port: 9090
      protocol: HTTP
      pathPrefix: /metrics

  # Template used to create the sandbox pod per session
  template:
    labels:
      app: code-foo
      component: runtime
    spec:
      serviceAccountName: code-interpreter-sa
      containers:
        - name: runtime
          image: ghcr.io/your-org/code-interpreter-runtime:latest
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          env:
            - name: PYTHONUNBUFFERED
              value: "1"
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
          volumeMounts:
            - name: tmp
              mountPath: /tmp
        # optional sidecar for logging/metrics
        - name: metrics
          image: ghcr.io/your-org/metrics-sidecar:latest
          ports:
            - name: metrics
              containerPort: 9090
              protocol: TCP
      restartPolicy: Always

  # After 15 minutes of inactivity, terminate the session’s sandbox
  sessionTimeout: 15m

  # Hard cap: session will be terminated after 8 hours regardless of activity
  maxSessionDuration: 8h
  ```

In order to expose the agent internally or externally, we also need to define a `AgentEndpoint` CRD, it can be used to bind to a specific `AgentRuntime` version.
With both `AgentRuntime` and `AgentEndpoint` published, users can access the agent runtime through the endpoint `https://<agent-frontend>:<frontend-port>/v1/namespaces/{agentNamespace}/agents/{agentName}/<agent specific path>?endpoint=<agent-endpoint>`.
While the `AgentRuntime` defines the desired state of the agent runtime environment, the `AgentEndpoint` provides a way to access a specific version of that runtime. If no `AgentEndpoint` is specified, the system will default to using the `DefaultVersion` defined in the `AgentRuntime` status.

```go
// AgentEndpoint defines the desired state of an agent endpoint.
// It is used to expose a specific agent runtime version to users.
type AgentEndpoint struct {
	metav1.TypeMeta `json:",inline"`
	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty,omitzero" protobuf:"bytes,1,opt,name=metadata"`
	// Spec defines the desired state of the AgentEndpoint.
	Spec AgentEndpointSpec `json:"spec" protobuf:"bytes,2,opt,name=spec"`
}

type AgentEndpointSpec struct {
	// Target specifies the target agent runtime.
	// +kubebuilder:validation:Required
	Target string `json:"target" protobuf:"bytes,1,opt,name=target"`
	// Version specifies the version of the agent runtime.
	// +kubebuilder:validation:Required
	Version string `json:"version" protobuf:"bytes,2,opt,name=version"`
}
```


#### CodeInterpreter Runtime CRD

```go
// CodeInterpreterRuntime defines the desired state of a code interpreter runtime environment.
//
// This runtime is designed for running potentially untrusted, LLM-generated code in an
// isolated sandbox, typically per user/session, with stricter security and resource controls
// compared to a generic AgentRuntime.
type CodeInterpreterRuntime struct {
	metav1.TypeMeta `json:",inline"`
	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty,omitzero" protobuf:"bytes,1,opt,name=metadata"`
	// Spec defines the desired state of the CodeInterpreterRuntime.
	Spec CodeInterpreterRuntimeSpec `json:"spec" protobuf:"bytes,2,opt,name=spec"`
	// Status represents the current state of the CodeInterpreterRuntime.
	Status CodeInterpreterRuntimeStatus `json:"status" protobuf:"bytes,3,opt,name=status"`
}

// CodeInterpreterRuntimeSpec describes how to create and manage code-interpreter sandboxes.
type CodeInterpreterRuntimeSpec struct {
	// Ports is a list of ports that the code interpreter runtime will expose.
	// These ports are typically used by the router / apiserver to proxy HTTP or gRPC
	// traffic into the sandbox (e.g., /execute, /files, /health).
	// If not specified, defaults to use agentcube's code interpreter.
	// +optional
	Ports []TargetPort `json:"ports,omitempty" protobuf:"bytes,1,rep,name=ports"`

	// Template describes the template that will be used to create a code interpreter sandbox.
	// This SHOULD be more locked down than a generic agent runtime (e.g. no hostPath,
	// restricted capabilities, read-only root filesystem, etc.).
	// +kubebuilder:validation:Required
	Template *CodeInterpreterSandboxTemplate `json:"template" protobuf:"bytes,2,opt,name=template"`

	// SessionTimeout describes the duration after which an inactive code-interpreter
	// session will be terminated. Any sandbox that has not received requests within
	// this duration is eligible for cleanup.
	// +kubebuilder:validation:Required
	// +kubebuilder:default="15m"
	SessionTimeout *metav1.Duration `json:"sessionTimeout,omitempty" protobuf:"bytes,3,opt,name=sessionTimeout"`

	// MaxSessionDuration describes the maximum duration for a code-interpreter session.
	// After this duration, the session will be terminated regardless of activity, to
	// prevent long-lived sandboxes from accumulating unbounded state.
	// +kubebuilder:validation:Required
	// +kubebuilder:default="8h"
	MaxSessionDuration *metav1.Duration `json:"maxSessionDuration,omitempty" protobuf:"bytes,4,opt,name=maxSessionDuration"`

	// WarmPoolSize specifies the number of pre-warmed sandboxes to maintain
	// for this code interpreter runtime. Pre-warmed sandboxes can reduce startup
	// latency for new sessions at the cost of additional resource usage.
	// +optional
	WarmPoolSize *int32 `json:"warmPoolSize,omitempty" protobuf:"varint,5,opt,name=warmPoolSize"`
}

// CodeInterpreterRuntimeStatus represents the observed state of a CodeInterpreterRuntime.
type CodeInterpreterRuntimeStatus struct {
	// DefaultVersion specifies the default version of the code interpreter runtime.
	// This is automatically set to the latest version or a controller-chosen default.
	// +optional
	DefaultVersion string `json:"defaultVersion,omitempty" protobuf:"bytes,1,opt,name=defaultVersion"`

	// Versions maps version identifiers (e.g. "v1", "v2-python-3.12") to container
	// image digests or other implementation details. The format is intentionally
	// opaque to the API consumer and interpreted by the controller.
	// +optional
	Versions map[string]string `json:"versions,omitempty" protobuf:"bytes,2,rep,name=versions"`
}

// CodeInterpreterSandboxTemplate mirrors SandboxTemplate but is kept separate in case
// we want to evolve code-interpreter specific defaults independently in the future.
// For now, it can be used in controllers or validation if a distinct type is helpful.
type CodeInterpreterSandboxTemplate struct {
	// Labels to apply to the sandbox Pod.
	// +optional
	Labels map[string]string `json:"labels,omitempty" protobuf:"bytes,1,rep,name=labels"`

	// Annotations to apply to the sandbox Pod.
	// +optional
	Annotations map[string]string `json:"annotations,omitempty" protobuf:"bytes,2,rep,name=annotations"`

	// RuntimeClassName specifies the Kubernetes RuntimeClass used to run the sandbox
	// (e.g., for kuasar / Kata-based isolation).
	// +optional
	RuntimeClassName *string `json:"runtimeClassName,omitempty" protobuf:"bytes,3,opt,name=runtimeClassName"`

	// Image indicates the container image to use for the code interpreter runtime.
	Image string `json:"image,omitempty" protobuf:"bytes,4,opt,name=image"`

	// Environment specifies the environment variables to set in the code interpreter runtime.
	Environment []corev1.EnvVar `json:"environment,omitempty" protobuf:"bytes,5,rep,name=environment"`

	// Entrypoint array. Not executed within a shell.
	// The container image's ENTRYPOINT is used if this is not provided.
	// +optional
	// +listType=atomic
	Command []string `json:"command,omitempty" protobuf:"bytes,6,rep,name=command"`

	// Arguments to the entrypoint.
	// The container image's CMD is used if this is not provided.
	// +optional
	Args []string `json:"args,omitempty" protobuf:"bytes,7,rep,name=args"`

	// Compute Resources required by this container.
	// More info: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
	// +optional
	Resources corev1.ResourceRequirements `json:"resources,omitempty" protobuf:"bytes,8,opt,name=resources"`
}
```

Similarly, below is an example of how to define a `CodeInterpreterRuntime` for a code interpreter runtime environment:

```yaml
apiVersion: runtime.example.com/v1
kind: CodeInterpreterRuntime
metadata:
  name: example-code-interpreter
spec:
  ports:
    - name: http
      port: 8080
  template:
    labels:
      app: example-code-interpreter
    annotations:
      description: "An example code interpreter runtime"
    runtimeClassName: "kata"
    image: "example/code-interpreter:latest"
    environment:
      - name: EXAMPLE_ENV
        value: "example"
    command:
      - "/usr/local/bin/code-interpreter"
    args:
      - "--config"
      - "/etc/code-interpreter/config.yaml"
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "1"
        memory: "1Gi"
  sessionTimeout: "15m"
  maxSessionDuration: "8h"
  warmPoolSize: 2
```

In order to expose the code interpreter internally or externally, we also need to define a `CodeInterpreterEndpoint` CRD, it can be used to bind to a specific `CodeInterpreterRuntime` version.
With both `CodeInterpreterRuntime` and `CodeInterpreterEndpoint` published, users can access the code interpreter runtime through the endpoint `https://<frontend>:<frontend-port>/v1/namespaces/{codeInterpreterNamespace}/codeinterpreters/{codeInterpreterName}/<code-interpreter specific path>?endpoint=<code-interpreter-endpoint>`.
 
`CodeInterpreterEndpoint` is similar as `AgentEndpoint`, it provides a way to access a specific version of that runtime. If no `CodeInterpreterEndpoint` is specified, the system will default to using the `DefaultVersion` defined in the `CodeInterpreterRuntime` status. For example, users can publish a python code interpreter runtime for different versions like `3.10`, `3.11`, `3.12`, then create different `CodeInterpreterEndpoint` to bind to different versions.

```go
// CodeInterpreterEndpoint defines the desired state of a code interpreter endpoint.
// It is used to expose a specific code interpreter runtime version to agents.
type CodeInterpreterEndpoint struct {
	metav1.TypeMeta `json:",inline"`
	// metadata is a standard object metadata
	// +optional
	metav1.ObjectMeta `json:"metadata,omitempty,omitzero" protobuf:"bytes,1,opt,name=metadata"`
	// Spec defines the desired state of the CodeInterpreterEndpoint.
	Spec CodeInterpreterEndpointSpec `json:"spec" protobuf:"bytes,2,opt,name=spec"`
}

type CodeInterpreterEndpointSpec struct {
	// Target specifies the target code interpreter runtime.
	// +kubebuilder:validation:Required
	Target string `json:"target" protobuf:"bytes,1,opt,name=target"`
	// Version specifies the version of the code interpreter runtime.
	// +kubebuilder:validation:Required
	Version string `json:"version" protobuf:"bytes,2,opt,name=version"`
}
```


### Alternatives

We can also design the `AgentRuntime` model each per version. That will make `AgentRuntime` version based, however, it will make managing multiple versions more complex, as users will need to create and manage separate `AgentRuntime` resources for each version they wish to support. But how will the system know which versions belong to the same `agent`. Then we would need to introduce another CRD to bind multiple `AgentRuntime` together.
