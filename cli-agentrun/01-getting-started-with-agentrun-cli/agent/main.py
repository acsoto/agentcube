#!/usr/bin/env python3
"""
Sentiment Analysis Agent - A practical example AI agent.

This agent provides sentiment analysis capabilities via HTTP API,
demonstrating how to build and deploy agents using AgentRun CLI.
"""

import os
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List
from datetime import datetime


class SentimentAnalyzer:
    """Simple rule-based sentiment analyzer for demonstration."""

    def __init__(self):
        # Positive and negative word lists for basic sentiment analysis
        self.positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'love', 'best', 'perfect', 'awesome', 'brilliant', 'outstanding',
            'superb', 'happy', 'joy', 'delighted', 'pleased', 'satisfied',
            'impressive', 'remarkable', 'exceptional', 'nice', 'beautiful'
        }

        self.negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'poor', 'worst',
            'hate', 'dislike', 'disappointed', 'sad', 'angry', 'upset',
            'frustrating', 'annoying', 'useless', 'pathetic', 'dreadful',
            'unpleasant', 'disgusting', 'inferior', 'mediocre', 'inadequate'
        }

        # Intensifiers
        self.intensifiers = {
            'very', 'extremely', 'incredibly', 'absolutely', 'really',
            'quite', 'totally', 'completely', 'utterly', 'highly'
        }

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of the given text.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary containing sentiment analysis results
        """
        if not text or not isinstance(text, str):
            return {
                "error": "Invalid input text",
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0
            }

        # Normalize text
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)

        if not words:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "word_count": 0
            }

        # Count sentiment words
        positive_count = 0
        negative_count = 0
        intensifier_count = 0

        for i, word in enumerate(words):
            # Check for intensifiers before sentiment words
            multiplier = 1.5 if i > 0 and words[i-1] in self.intensifiers else 1.0

            if word in self.positive_words:
                positive_count += multiplier
            elif word in self.negative_words:
                negative_count += multiplier
            elif word in self.intensifiers:
                intensifier_count += 1

        # Calculate sentiment score
        total_sentiment_words = positive_count + negative_count

        if total_sentiment_words == 0:
            sentiment = "neutral"
            score = 0.0
            confidence = 0.0
        else:
            score = (positive_count - negative_count) / len(words)
            confidence = min(total_sentiment_words / len(words) * 2, 1.0)

            if score > 0.05:
                sentiment = "positive"
            elif score < -0.05:
                sentiment = "negative"
            else:
                sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "confidence": round(confidence, 4),
            "word_count": len(words),
            "positive_words_found": int(positive_count),
            "negative_words_found": int(negative_count),
            "intensifiers_found": intensifier_count
        }

    def batch_analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple texts at once."""
        return [self.analyze(text) for text in texts]


class SentimentAgentHandler(BaseHTTPRequestHandler):
    """HTTP handler for the Sentiment Analysis Agent."""

    analyzer = SentimentAnalyzer()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._send_json_response({
                "status": "healthy",
                "agent": "sentiment-analysis-agent",
                "version": "1.0.0",
                "timestamp": self._get_timestamp()
            })
        elif self.path == '/':
            self._send_json_response({
                "name": "Sentiment Analysis Agent",
                "description": "Analyzes sentiment of text inputs",
                "version": "1.0.0",
                "endpoints": [
                    "GET /health - Health check",
                    "POST /analyze - Analyze single text",
                    "POST /batch - Analyze multiple texts",
                    "GET / - Agent information"
                ]
            })
        else:
            self._send_error(404, "Endpoint not found")

    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/analyze':
            self._handle_analyze()
        elif self.path == '/batch':
            self._handle_batch()
        elif self.path == '/':
            # Support AgentCube invocation format
            self._handle_invoke()
        else:
            self._send_error(404, "Endpoint not found")

    def _handle_analyze(self):
        """Handle single text analysis."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            text = data.get('text', '')
            if not text:
                self._send_error(400, "Text field is required")
                return

            result = self.analyzer.analyze(text)
            result['timestamp'] = self._get_timestamp()
            result['agent'] = 'sentiment-analysis-agent'

            self._send_json_response(result)

        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON payload")
        except Exception as e:
            self._send_error(500, f"Internal error: {str(e)}")

    def _handle_batch(self):
        """Handle batch text analysis."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            texts = data.get('texts', [])
            if not texts or not isinstance(texts, list):
                self._send_error(400, "texts field must be a non-empty array")
                return

            results = self.analyzer.batch_analyze(texts)

            response = {
                'results': results,
                'count': len(results),
                'timestamp': self._get_timestamp(),
                'agent': 'sentiment-analysis-agent'
            }

            self._send_json_response(response)

        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON payload")
        except Exception as e:
            self._send_error(500, f"Internal error: {str(e)}")

    def _handle_invoke(self):
        """Handle AgentCube-style invocation."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            # Support both 'text' and 'prompt' fields
            text = data.get('text') or data.get('prompt', '')

            if not text:
                self._send_error(400, "text or prompt field is required")
                return

            result = self.analyzer.analyze(text)
            result['timestamp'] = self._get_timestamp()
            result['agent'] = 'sentiment-analysis-agent'
            result['input'] = text

            self._send_json_response(result)

        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON payload")
        except Exception as e:
            self._send_error(500, f"Internal error: {str(e)}")

    def _send_json_response(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = json.dumps(data, indent=2)
        self.wfile.write(response.encode('utf-8'))

    def _send_error(self, status_code: int, message: str):
        """Send error response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        error_response = json.dumps({
            "error": message,
            "status_code": status_code,
            "timestamp": self._get_timestamp()
        }, indent=2)

        self.wfile.write(error_response.encode('utf-8'))

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()

    def log_message(self, format, *args):
        """Custom logging to reduce noise."""
        if os.environ.get('DEBUG', 'false').lower() == 'true':
            super().log_message(format, *args)


def main():
    """Main function to run the Sentiment Analysis Agent."""
    port = int(os.environ.get('PORT', 8080))

    print("=" * 60)
    print("🤖 Sentiment Analysis Agent")
    print("=" * 60)
    print(f"📡 Starting server on port {port}")
    print(f"🏥 Health check: http://localhost:{port}/health")
    print(f"📊 Analyze endpoint: http://localhost:{port}/analyze")
    print(f"📚 Batch endpoint: http://localhost:{port}/batch")
    print(f"🎯 Invoke endpoint: http://localhost:{port}/")
    print("=" * 60)

    server_address = ('', port)
    httpd = HTTPServer(server_address, SentimentAgentHandler)

    try:
        print(f"✅ Sentiment Analysis Agent is running!")
        print(f"💡 Press Ctrl+C to stop the server")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Shutting down Sentiment Analysis Agent...")
        httpd.server_close()
        print("👋 Goodbye!")


if __name__ == '__main__':
    main()
