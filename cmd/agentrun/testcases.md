## Test Case 1: CLI Deployment Test

- **Objective:** Verify that an agent can be packaged, built, published, and deployed into a specific Kubernetes namespace.
- **Preconditions:**
    - Kubernetes cluster is running
    - `kubectl` CLI is installed and configured
    - `agentrun` plugin is available
- **Steps:**

    1. Run `kubectl create namespace test-agent-space`
    2. Run `kubectl agentrun pack`
    3. Run `kubectl agentrun build`
    4. Run `kubectl agentrun publish`
    
- **Expected Result:**
  
    - A new namespace `test-agent-space` is created
    - The agent is successfully packaged, built, and published
    - The agent is deployed to the `test-agent-space` namespace

## Test Case 2: Code Interpreter Workflow Test

**Objective:** Validate that the Code Interpreter can handle file upload, dependency installation, model training, and artifact download with Python-SDK.

```python
from agentcube import CodeInterpreterClient

# Create a CodeInterpreterClient instance
code_interpreter = CodeInterpreterClient(
    ttl=3600,  # Time-to-live in seconds
    image="sandbox:latest",  # Container image to use
)

try:
    # Step 1: Upload dependencies file (WriteFile API)
    code_interpreter.write_file(
        content="pandas\nnumpy\nscikit-learn\nmatplotlib",
        remote_path="/workspace/requirements.txt"
    )

    # Step 2: Install dependencies (Execute API)
    code_interpreter.execute_command("pip install -r /workspace/requirements.txt")

    # Step 3: Upload training data (WriteFile API)
    code_interpreter.upload_file(
        local_path="./data/train.csv",
        remote_path="/workspace/train.csv"
    )

    # Step 4: Train model (Execute API)
    training_code = """
    import pandas as pd
    from sklearn.linear_model import LinearRegression
    import pickle
    df = pd.read_csv('/workspace/train.csv')
    X, y = df[['feature1', 'feature2']], df['target']
    model = LinearRegression().fit(X, y)
    pickle.dump(model, open('/workspace/model.pkl', 'wb'))
    print(f'Model R² score: {model.score(X, y):.4f}')
    """
    result = code_interpreter.run_code("python", training_code)

    print(result)

    # Step 5: Download trained model (ReadFile API)
    code_interpreter.download_file(
        remote_path="/workspace/model.pkl",
        local_path="./models/model.pkl"
    )

    print("Workflow completed successfully!")

finally:
    code_interpreter.stop()
```
## Integration Test: LangChain Agent with SiliconFlow + Code Interpreter

**Test Agent Source**

```python
from fastapi import FastAPI, Request
import uvicorn
from langchain.agents import initialize_agent, Tool
from agentcube import CodeInterpreterClient
from langchain.llms import SiliconFlow

# Initialize Code Interpreter client
ci_client = CodeInterpreterClient(ttl=600, image="sandbox:latest")

def run_python_code(code: str) -> str:
    """Wrapper to run Python code inside Code Interpreter."""
    return ci_client.run_code("python", code)

# Define LangChain tool
tools = [
    Tool(
        name="CodeInterpreter",
        func=run_python_code,
        description="Executes Python code inside a sandboxed Code Interpreter environment."
    )
]

# Initialize SiliconFlow LLM
llm = SiliconFlow(
    model="siliconflow/gpt-4",   # Adjust to SiliconFlow’s available models
    api_key="YOUR_SILICONFLOW_API_KEY"
)

# Create agent
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True
)

# FastAPI app
app = FastAPI()

@app.post("/run")
async def run_agent(request: Request):
    data = await request.json()
    query = data.get("query", "")
    response = agent.run(query)
    return {"response": response}

@app.on_event("shutdown")
def shutdown_event():
    ci_client.stop()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

```
### Deployment Instructions
Similar to **Test Case 1**, use the CLI to package, build, and publish this agent into the cluster:

```bash
kubectl create namespace test-agent-space
kubectl agentrun pack
kubectl agentrun build
kubectl agentrun publish
```

This workflow ensures the agent is deployed into the `test-agent-space` namespace and exposed as a FastAPI service on port **8080**.

### Expected Result

- The agent is successfully packaged, built, and published via CLI into the `test-agent-space` namespace
- The FastAPI service runs on port **8080** inside the cluster
- Sending a POST request to `/run` with a JSON payload such as: 
    ```
    curl -X POST "http://<agent-service-url>:8080/run" \
         -H "Content-Type: application/json" \
         -d '{"query": "Use CodeInterpreter to execute: import math;   print(math.sqrt(49))"}'
    ```
	returns:
	```json
	{
		"response": "Square root of 49 is 7.0"
	}
	```

- The workflow executes end-to-end, with **SiliconFlow** providing reasoning and **Code Interpreter** handling code execution
