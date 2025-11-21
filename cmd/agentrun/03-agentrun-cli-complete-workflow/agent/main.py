#!/usr/bin/env python3
"""
Conversational Assistant Agent

A sample AI agent demonstrating best practices for building agents with AgentRun CLI.
This agent provides a conversational interface with tool-calling capabilities.

Features:
- HTTP-based API for agent invocation
- Tool calling (weather, calculator, time)
- Health check endpoint
- Structured logging
- Error handling
"""

import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

# Import our tools module
import tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Conversational Assistant Agent."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/health':
            self._handle_health()
        elif path == '/':
            self._handle_info()
        elif path == '/tools':
            self._handle_tools_info()
        else:
            self._send_error(404, f"Endpoint not found: {path}")

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/' or path == '/invoke':
            self._handle_invoke()
        elif path == '/tools/weather':
            self._handle_tool_weather()
        elif path == '/tools/calculator':
            self._handle_tool_calculator()
        elif path == '/tools/time':
            self._handle_tool_time()
        else:
            self._send_error(404, f"Endpoint not found: {path}")

    def _handle_health(self):
        """Handle health check requests."""
        logger.info("Health check requested")
        self._send_json_response({
            "status": "healthy",
            "agent": "conversational-assistant",
            "version": "1.0.0"
        })

    def _handle_info(self):
        """Handle agent information requests."""
        logger.info("Agent info requested")
        self._send_json_response({
            "name": "Conversational Assistant Agent",
            "version": "1.0.0",
            "description": "A conversational agent with tool-calling capabilities",
            "endpoints": [
                "GET /health - Health check",
                "GET / - Agent information",
                "GET /tools - Available tools information",
                "POST /invoke - Main agent invocation endpoint",
                "POST /tools/weather - Get weather information",
                "POST /tools/calculator - Perform calculations",
                "POST /tools/time - Get current time"
            ],
            "tools": list(tools.AVAILABLE_TOOLS.keys())
        })

    def _handle_tools_info(self):
        """Handle tools information requests."""
        logger.info("Tools info requested")
        tools_info = tools.get_tools_info()
        self._send_json_response({
            "tools": tools_info,
            "count": len(tools_info)
        })

    def _handle_invoke(self):
        """Handle main agent invocation requests."""
        try:
            # Parse request body
            data = self._parse_request_body()

            if not data:
                self._send_error(400, "Request body is required")
                return

            # Extract prompt or task
            prompt = data.get('prompt', data.get('task', ''))
            if not prompt:
                self._send_error(400, "Prompt or task is required")
                return

            logger.info(f"Agent invoked with prompt: {prompt[:100]}...")

            # Process the request
            response = self._process_agent_request(prompt, data)

            self._send_json_response(response)

        except Exception as e:
            logger.error(f"Error processing invocation: {str(e)}")
            self._send_error(500, f"Internal server error: {str(e)}")

    def _handle_tool_weather(self):
        """Handle weather tool requests."""
        try:
            data = self._parse_request_body()
            city = data.get('city', '')

            if not city:
                self._send_error(400, "City parameter is required")
                return

            logger.info(f"Weather tool called for city: {city}")

            result = tools.get_weather(city)
            self._send_json_response(result)

        except Exception as e:
            logger.error(f"Error in weather tool: {str(e)}")
            self._send_error(500, str(e))

    def _handle_tool_calculator(self):
        """Handle calculator tool requests."""
        try:
            data = self._parse_request_body()
            expression = data.get('expression', '')

            if not expression:
                self._send_error(400, "Expression parameter is required")
                return

            logger.info(f"Calculator tool called with expression: {expression}")

            result = tools.calculate(expression)
            self._send_json_response(result)

        except Exception as e:
            logger.error(f"Error in calculator tool: {str(e)}")
            self._send_error(500, str(e))

    def _handle_tool_time(self):
        """Handle time tool requests."""
        try:
            data = self._parse_request_body()
            timezone = data.get('timezone', 'UTC')

            logger.info(f"Time tool called for timezone: {timezone}")

            result = tools.get_time(timezone)
            self._send_json_response(result)

        except Exception as e:
            logger.error(f"Error in time tool: {str(e)}")
            self._send_error(500, str(e))

    def _process_agent_request(self, prompt: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an agent request and generate a response.

        In a real agent, this would involve:
        - Understanding the prompt using NLP
        - Determining which tools to call
        - Orchestrating tool calls
        - Generating a natural language response

        For this demo, we'll implement simple keyword-based routing.

        Args:
            prompt: User prompt or task
            data: Additional request data

        Returns:
            Dictionary containing the agent response
        """
        prompt_lower = prompt.lower()

        # Simple keyword-based routing for demo purposes
        response = {
            "prompt": prompt,
            "agent": "conversational-assistant",
            "timestamp": tools.datetime.now().isoformat()
        }

        # Check for weather-related queries
        if any(word in prompt_lower for word in ['weather', 'temperature', 'forecast']):
            # Try to extract city name (simplified)
            city = data.get('city', 'Shanghai')  # Default city
            weather_result = tools.get_weather(city)
            response["tool_used"] = "weather"
            response["tool_result"] = weather_result
            response["response"] = f"The weather in {weather_result['city']} is {weather_result['condition']} with a temperature of {weather_result['temperature']}°{weather_result['temperature_unit']} and humidity at {weather_result['humidity']}%."

        # Check for calculation-related queries
        elif any(word in prompt_lower for word in ['calculate', 'compute', 'math', '+', '-', '*', '/']):
            # Try to extract expression
            expression = data.get('expression', '')
            if expression:
                calc_result = tools.calculate(expression)
                response["tool_used"] = "calculator"
                response["tool_result"] = calc_result
                if calc_result['success']:
                    response["response"] = f"The result of {calc_result['expression']} is {calc_result['result']}."
                else:
                    response["response"] = f"I encountered an error calculating the expression: {calc_result['error']}"
            else:
                response["response"] = "I can help you with calculations. Please provide an expression in the 'expression' field."

        # Check for time-related queries
        elif any(word in prompt_lower for word in ['time', 'date', 'clock']):
            timezone = data.get('timezone', 'UTC')
            time_result = tools.get_time(timezone)
            response["tool_used"] = "time"
            response["tool_result"] = time_result
            response["response"] = f"The current time in {time_result['timezone']} is {time_result['time']} on {time_result['day_of_week']}, {time_result['date']}."

        # Default response
        else:
            available_tools = list(tools.AVAILABLE_TOOLS.keys())
            response["response"] = f"Hello! I'm a conversational assistant. I received your message: '{prompt}'. I can help you with: {', '.join(available_tools)}. How can I assist you?"

        return response

    def _parse_request_body(self) -> Optional[Dict[str, Any]]:
        """
        Parse JSON request body.

        Returns:
            Parsed JSON data or None if parsing fails
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return None

            post_data = self.rfile.read(content_length)
            return json.loads(post_data.decode('utf-8'))

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing request body: {str(e)}")
            return None

    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """
        Send JSON response.

        Args:
            data: Data to send as JSON
            status_code: HTTP status code
        """
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = json.dumps(data, indent=2)
        self.wfile.write(response.encode('utf-8'))

    def _send_error(self, status_code: int, message: str):
        """
        Send error response.

        Args:
            status_code: HTTP status code
            message: Error message
        """
        logger.error(f"Error {status_code}: {message}")

        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        error_response = json.dumps({
            "error": message,
            "status_code": status_code
        }, indent=2)

        self.wfile.write(error_response.encode('utf-8'))

    def log_message(self, format, *args):
        """Override to use our logger instead of printing to stderr."""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    """Main function to run the Conversational Assistant Agent."""
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 8080))

    logger.info(f"Starting Conversational Assistant Agent on port {port}")
    logger.info(f"Health check: http://localhost:{port}/health")
    logger.info(f"Agent info: http://localhost:{port}/")
    logger.info(f"Tools info: http://localhost:{port}/tools")
    logger.info(f"Invoke endpoint: http://localhost:{port}/invoke")

    # Create and start the HTTP server
    server_address = ('', port)
    httpd = HTTPServer(server_address, AgentHandler)

    try:
        logger.info(f"Conversational Assistant Agent is running on port {port}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down Conversational Assistant Agent")
        httpd.server_close()


if __name__ == '__main__':
    main()
