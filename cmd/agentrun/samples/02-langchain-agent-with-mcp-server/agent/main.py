"""
LangChain Agent with MCP Server Integration

This agent demonstrates how to integrate LangChain with an MCP server
to provide enhanced tool-calling capabilities.

The agent:
- Connects to an MCP server via HTTP transport
- Converts MCP tools to LangChain tools using langchain-mcp-adapters
- Provides a FastAPI endpoint for user interaction
- Can be deployed separately from the MCP server

This showcases a microservices architecture for AI agents where:
- MCP server provides the tools
- LangChain agent orchestrates the tools
- Both can be deployed and scaled independently
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import timedelta

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.llms import OpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

# MCP imports
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# ============================================================================
# Configuration
# ============================================================================

# MCP Server URL - can be configured via environment variable
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-utility-server.agentrun.svc.cluster.local:8000/mcp")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
USE_MOCK_MODE = not OPENAI_API_KEY

# Agent configuration
AGENT_PORT = int(os.getenv("AGENT_PORT", "8080"))


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="LangChain Agent with MCP Server",
    description="An agent that integrates LangChain with MCP server tools",
    version="1.0.0"
)


# ============================================================================
# Request/Response Models
# ============================================================================

class AgentRequest(BaseModel):
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500


class AgentResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None
    tools_used: Optional[List[str]] = None


class ToolInfo(BaseModel):
    name: str
    description: str


# ============================================================================
# MCP Tool Conversion
# ============================================================================

class MCPToolConverter:
    """Converts MCP tools to LangChain tools"""

    @staticmethod
    async def get_mcp_tools(mcp_url: str) -> List[Tool]:
        """
        Connect to MCP server and retrieve tools, converting them to LangChain tools
        """
        try:
            headers = {}
            tools = []

            async with streamablehttp_client(
                mcp_url,
                headers,
                timeout=timedelta(seconds=30),
                terminate_on_close=False
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tool_result = await session.list_tools()

                    for mcp_tool in tool_result.tools:
                        # Create a LangChain tool from MCP tool
                        langchain_tool = Tool(
                            name=mcp_tool.name,
                            description=mcp_tool.description or f"Tool: {mcp_tool.name}",
                            func=lambda x, tool_name=mcp_tool.name: MCPToolConverter._call_mcp_tool_sync(
                                mcp_url, tool_name, x
                            )
                        )
                        tools.append(langchain_tool)

            return tools
        except Exception as e:
            print(f"Error connecting to MCP server: {e}")
            return []

    @staticmethod
    def _call_mcp_tool_sync(mcp_url: str, tool_name: str, args_str: str) -> str:
        """
        Synchronous wrapper to call MCP tool from LangChain
        """
        return asyncio.run(MCPToolConverter._call_mcp_tool(mcp_url, tool_name, args_str))

    @staticmethod
    async def _call_mcp_tool(mcp_url: str, tool_name: str, args_str: str) -> str:
        """
        Call an MCP tool with the given arguments
        """
        try:
            # Parse arguments if it's JSON-like
            import json
            try:
                args = json.loads(args_str)
            except:
                # If not JSON, treat as single string argument
                args = {"input": args_str}

            headers = {}
            async with streamablehttp_client(
                mcp_url,
                headers,
                timeout=timedelta(seconds=30),
                terminate_on_close=False
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name=tool_name, arguments=args)
                    return str(result.content[0].text)
        except Exception as e:
            return f"Error calling tool {tool_name}: {str(e)}"


# ============================================================================
# Agent Management
# ============================================================================

class AgentManager:
    """Manages the LangChain agent and MCP connection"""

    def __init__(self):
        self.mcp_tools = []
        self.agent = None
        self.agent_executor = None

    async def initialize(self):
        """Initialize the agent with MCP tools"""
        print(f"Connecting to MCP server at: {MCP_SERVER_URL}")

        # Get MCP tools
        self.mcp_tools = await MCPToolConverter.get_mcp_tools(MCP_SERVER_URL)
        print(f"Loaded {len(self.mcp_tools)} tools from MCP server")

        if not USE_MOCK_MODE and self.mcp_tools:
            # Create LangChain agent with OpenAI
            llm = OpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)

            # Create agent prompt
            template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

            prompt = PromptTemplate.from_template(template)

            # Create agent
            self.agent = create_react_agent(llm, self.mcp_tools, prompt)
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.mcp_tools,
                verbose=True,
                handle_parsing_errors=True
            )
            print("Agent initialized successfully with OpenAI and MCP tools")
        else:
            print("Running in MOCK MODE (no OpenAI API key or no MCP tools)")

    async def invoke(self, prompt: str) -> Dict[str, Any]:
        """Invoke the agent with a prompt"""
        if USE_MOCK_MODE or not self.agent_executor:
            # Mock response
            available_tools = [tool.name for tool in self.mcp_tools] if self.mcp_tools else ["No tools available"]
            return {
                "response": f"[Mock Mode] Received prompt: '{prompt}'. "
                            f"In production, this would use the LangChain agent with MCP tools. "
                            f"Available tools from MCP server: {', '.join(available_tools)}. "
                            f"Set OPENAI_API_KEY environment variable for real agent responses.",
                "success": True,
                "tools_used": []
            }

        try:
            # Invoke the agent
            result = await asyncio.to_thread(
                self.agent_executor.invoke,
                {"input": prompt}
            )

            return {
                "response": result.get("output", "No response generated"),
                "success": True,
                "tools_used": []  # Could track tools used from intermediate steps
            }
        except Exception as e:
            return {
                "response": "",
                "success": False,
                "error": str(e)
            }

    def get_tools_info(self) -> List[Dict[str, str]]:
        """Get information about available tools"""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.mcp_tools
        ]


# ============================================================================
# Global Agent Manager
# ============================================================================

agent_manager = AgentManager()


# ============================================================================
# API Endpoints
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    await agent_manager.initialize()


@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "LangChain Agent with MCP Server",
        "version": "1.0.0",
        "status": "running",
        "mcp_server": MCP_SERVER_URL,
        "mode": "mock" if USE_MOCK_MODE else "production",
        "available_tools": len(agent_manager.mcp_tools)
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/tools")
async def list_tools():
    """List available tools from MCP server"""
    return {
        "tools": agent_manager.get_tools_info(),
        "count": len(agent_manager.mcp_tools),
        "mcp_server": MCP_SERVER_URL
    }


@app.post("/invoke", response_model=AgentResponse)
async def invoke_agent(request: AgentRequest):
    """
    Invoke the agent with a prompt.

    The agent will use the MCP server tools to fulfill the request.
    """
    try:
        result = await agent_manager.invoke(request.prompt)

        return AgentResponse(
            response=result["response"],
            success=result["success"],
            error=result.get("error"),
            tools_used=result.get("tools_used", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/")
async def invoke_agent_root(request: AgentRequest):
    """Alternative endpoint for agent invocation (for compatibility)"""
    return await invoke_agent(request)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("LangChain Agent with MCP Server")
    print("=" * 60)
    print(f"Agent Port: {AGENT_PORT}")
    print(f"MCP Server URL: {MCP_SERVER_URL}")
    print(f"Mode: {'Mock (no OpenAI API key)' if USE_MOCK_MODE else 'Production'}")
    print("=" * 60)
    print("\nStarting agent server...")
    print("Endpoints:")
    print(f"  - GET  /         : Service information")
    print(f"  - GET  /health   : Health check")
    print(f"  - GET  /tools    : List available MCP tools")
    print(f"  - POST /invoke   : Invoke agent with prompt")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
