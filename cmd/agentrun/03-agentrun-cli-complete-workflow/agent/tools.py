#!/usr/bin/env python3
"""
Tools for the Conversational Assistant Agent

This module provides various tools that the agent can use to perform tasks:
- Weather: Get weather information for a city
- Calculator: Perform mathematical calculations
- Time: Get current time in different timezones
"""

import json
import math
import operator
from datetime import datetime
from typing import Dict, Any
import random


def get_weather(city: str) -> Dict[str, Any]:
    """
    Get weather information for a specific city.

    In a real application, this would call a weather API.
    For this demo, it returns simulated weather data.

    Args:
        city: Name of the city to get weather for

    Returns:
        Dictionary containing weather information
    """
    # Simulated weather data for demo purposes
    weather_conditions = ["sunny", "cloudy", "rainy", "partly cloudy", "clear"]

    # Generate realistic temperature based on random selection
    temperature = random.randint(15, 30)
    condition = random.choice(weather_conditions)
    humidity = random.randint(40, 80)

    return {
        "city": city,
        "temperature": temperature,
        "temperature_unit": "Celsius",
        "condition": condition,
        "humidity": humidity,
        "humidity_unit": "percent",
        "timestamp": datetime.now().isoformat(),
        "note": "This is simulated weather data for demonstration purposes"
    }


def calculate(expression: str) -> Dict[str, Any]:
    """
    Calculate the result of a mathematical expression.

    Supports basic arithmetic operations and common mathematical functions.

    Args:
        expression: A mathematical expression as a string
                   (e.g., "2 + 3 * 4", "sqrt(16)", "sin(pi/2)")

    Returns:
        Dictionary containing the result or error message
    """
    try:
        # Define safe functions that can be used in expressions
        safe_dict = {
            "__builtins__": {},
            # Basic functions
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow,
            # Math functions
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10, "exp": math.exp,
            "pi": math.pi, "e": math.e,
            "ceil": math.ceil, "floor": math.floor,
            "degrees": math.degrees, "radians": math.radians,
            # Basic operators (for explicit use)
            "add": operator.add, "sub": operator.sub,
            "mul": operator.mul, "truediv": operator.truediv,
        }

        # Evaluate the expression safely
        result = eval(expression, safe_dict)

        return {
            "expression": expression,
            "result": str(result),
            "success": True
        }

    except ZeroDivisionError:
        return {
            "expression": expression,
            "error": "Division by zero",
            "success": False
        }
    except ValueError as e:
        return {
            "expression": expression,
            "error": f"Invalid value - {str(e)}",
            "success": False
        }
    except SyntaxError:
        return {
            "expression": expression,
            "error": "Invalid mathematical expression",
            "success": False
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e),
            "success": False
        }


def get_time(timezone: str = "UTC") -> Dict[str, Any]:
    """
    Get the current time in the specified timezone.

    For this demo, returns UTC time with timezone information.
    In a real application, this would handle actual timezone conversions.

    Args:
        timezone: Timezone identifier (e.g., "UTC", "America/New_York", "Asia/Shanghai")

    Returns:
        Dictionary containing time information
    """
    current_time = datetime.now()

    # For demo purposes, we'll just show UTC time
    # In a real implementation, you'd use pytz or zoneinfo for proper timezone handling

    return {
        "timezone": timezone,
        "datetime": current_time.isoformat(),
        "date": current_time.strftime("%Y-%m-%d"),
        "time": current_time.strftime("%H:%M:%S"),
        "day_of_week": current_time.strftime("%A"),
        "timestamp": current_time.timestamp(),
        "note": "This shows UTC time. In production, use proper timezone libraries."
    }


# Tool registry for easy lookup
AVAILABLE_TOOLS = {
    "weather": {
        "function": get_weather,
        "description": "Get weather information for a city",
        "parameters": {
            "city": {
                "type": "string",
                "description": "Name of the city",
                "required": True
            }
        }
    },
    "calculator": {
        "function": calculate,
        "description": "Calculate the result of a mathematical expression",
        "parameters": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate",
                "required": True
            }
        }
    },
    "time": {
        "function": get_time,
        "description": "Get current time in a specific timezone",
        "parameters": {
            "timezone": {
                "type": "string",
                "description": "Timezone identifier (default: UTC)",
                "required": False,
                "default": "UTC"
            }
        }
    }
}


def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool by name with given parameters.

    Args:
        tool_name: Name of the tool to execute
        parameters: Dictionary of parameters for the tool

    Returns:
        Dictionary containing tool execution result
    """
    if tool_name not in AVAILABLE_TOOLS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(AVAILABLE_TOOLS.keys())
        }

    tool_config = AVAILABLE_TOOLS[tool_name]
    tool_function = tool_config["function"]

    try:
        # Execute the tool function with provided parameters
        result = tool_function(**parameters)
        return {
            "success": True,
            "tool": tool_name,
            "result": result
        }
    except TypeError as e:
        return {
            "success": False,
            "error": f"Invalid parameters for tool {tool_name}: {str(e)}",
            "expected_parameters": tool_config["parameters"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }


def get_tools_info() -> Dict[str, Any]:
    """
    Get information about all available tools.

    Returns:
        Dictionary containing tool descriptions and parameters
    """
    tools_info = {}
    for tool_name, tool_config in AVAILABLE_TOOLS.items():
        tools_info[tool_name] = {
            "description": tool_config["description"],
            "parameters": tool_config["parameters"]
        }
    return tools_info
