"""
Simple LangChain Agent Application for Testing AgentRun CLI

This is a minimal agent application that demonstrates:
- LangChain agent with tools
- FastAPI web server
- JSON payload handling
- Ready for containerization with AgentRun CLI
"""

import os
import json
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Updated imports for modern LangChain
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import Tool
from langchain import hub


# Initialize FastAPI app
app = FastAPI(
    title="Simple LangChain Test Agent",
    description="A simple agent for testing AgentRun CLI pack and build commands",
    version="1.0.0"
)


# Request/Response models
class AgentRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500


class AgentResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None


# Simple calculator tool
def calculate(expression: str) -> str:
    """
    Simple calculator that evaluates mathematical expressions.

    Args:
        expression: A mathematical expression like "2 + 2" or "10 * 5"

    Returns:
        The result of the calculation
    """
    try:
        # Only allow basic arithmetic operations for safety
        allowed_chars = set("0123456789+-*/() .")
        if not all(c in allowed_chars for c in expression):
            return "Error: Only basic arithmetic operations are allowed"

        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error calculating: {str(e)}"


# Weather tool (mock)
def get_weather(location: str) -> str:
    """
    Get weather information for a location (mock implementation).

    Args:
        location: City name or location

    Returns:
        Weather information string
    """
    # This is a mock implementation - returns static data
    mock_weather = {
        "shanghai": "Sunny, 22°C, Humidity 60%",
        "beijing": "Cloudy, 18°C, Humidity 45%",
        "new york": "Rainy, 15°C, Humidity 80%",
        "london": "Foggy, 12°C, Humidity 75%",
    }

    location_lower = location.lower()
    weather = mock_weather.get(location_lower, f"Weather data not available for {location}")
    return weather


# Initialize tools
tools = [
    Tool(
        name="Calculator",
        func=calculate,
        description="Useful for performing mathematical calculations. Input should be a mathematical expression like '2 + 2' or '10 * 5'."
    ),
    Tool(
        name="Weather",
        func=get_weather,
        description="Useful for getting weather information for a city. Input should be a city name like 'Shanghai' or 'New York'."
    )
]


# Initialize LLM and agent (will be created per request to allow custom parameters)
def create_agent(temperature: float = 0.7):
    """Create a new agent instance with specified parameters."""

    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # For testing without OpenAI, we'll use a mock response
        return None

    try:
        llm = OpenAI(
            temperature=temperature,
            openai_api_key=api_key,
            max_tokens=500
        )

        # Get the react prompt from hub
        prompt = hub.pull("hwchase17/react")

        # Create the agent
        agent = create_react_agent(llm, tools, prompt)

        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )

        return agent_executor
    except Exception as e:
        print(f"Error creating agent: {e}")
        return None


@app.get("/health")
async def health():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/tools")
async def list_tools():
    """List available tools."""
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description
            }
            for tool in tools
        ]
    }


@app.post("/", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest):
    """
    Invoke the agent with a prompt.

    Args:
        request: AgentRequest containing prompt and optional parameters

    Returns:
        AgentResponse with the agent's response
    """
    try:
        # Create agent with specified temperature
        agent = create_agent(temperature=request.temperature)

        if agent is None:
            # Mock response when OpenAI API key is not available
            response_text = f"[Mock Response] Received prompt: '{request.prompt}'. "

            # Provide different responses based on prompt content
            if "calculate" in request.prompt.lower() or any(c in request.prompt for c in "+-*/"):
                response_text += "This would normally use the Calculator tool to perform the calculation."
            elif "weather" in request.prompt.lower():
                response_text += "This would normally use the Weather tool to fetch weather information."
            else:
                response_text += "This would normally process your request using LangChain with OpenAI."

            response_text += " (Set OPENAI_API_KEY environment variable for real agent responses)"

            return AgentResponse(
                response=response_text,
                success=True,
                error=None
            )

        # Run the agent with invoke method (updated API)
        result = agent.invoke({"input": request.prompt})

        return AgentResponse(
            response=result["output"],
            success=True,
            error=None
        )

    except Exception as e:
        return AgentResponse(
            response="",
            success=False,
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable or use default
    port = int(os.getenv("PORT", "8080"))

    print(f"Starting LangChain Test Agent on port {port}...")
    print(f"OpenAI API Key configured: {bool(os.getenv('OPENAI_API_KEY'))}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )