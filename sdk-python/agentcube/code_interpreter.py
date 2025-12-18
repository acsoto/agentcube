import os
import base64
import logging
import json
import shlex
import time
from typing import Optional, Any, List, Union, Dict

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from agentcube.exceptions import CommandExecutionError
from agentcube.utils.log import get_logger

# Suppress InsecureRequestWarning for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Hardcoded authentication token - must match PicoD's AuthToken
AUTH_TOKEN = "agentcube-secret-token"

class CodeInterpreterClient:
    """
    AgentCube Code Interpreter Client for direct communication with PicoD.
    
    This client directly interacts with a PicoD instance, providing methods
    to execute code and manage files within it, bypassing WorkloadManager and Router.
    """
    
    def __init__(
        self,
        picod_url: str,
        verbose: bool = False,
        verify_ssl: bool = False
    ):
        """
        Initialize the Code Interpreter Client for direct PicoD communication.
        
        Args:
            picod_url: The base URL of the PicoD instance (e.g., "https://localhost:8080").
            verbose: Enable debug logging.
            verify_ssl: Verify SSL certificate. Defaults to False for self-signed certificates.
        """
        self.picod_url = picod_url.rstrip('/') # Ensure no trailing slash
        self.verbose = verbose
        self.verify_ssl = verify_ssl
        
        # Configure Logger
        level = logging.DEBUG if verbose else logging.INFO
        self.logger = get_logger(__name__, level=level)
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {AUTH_TOKEN}"
        })
        self.session.verify = verify_ssl

        self.logger.info(f"CodeInterpreterClient initialized for PicoD at {self.picod_url} (SSL Verify: {self.verify_ssl})")

    def __enter__(self):
        self.logger.debug("Entering CodeInterpreterClient context.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.debug("Exiting CodeInterpreterClient context.")
        self.close()

    def close(self):
        """Close the underlying requests session."""
        self.session.close()
        self.logger.info("CodeInterpreterClient session closed.")

    def _request(self, method: str, endpoint: str, body: Optional[bytes] = None, **kwargs) -> requests.Response:
        """Make an authenticated request to PicoD."""
        url = f"{self.picod_url}{endpoint}"
        
        headers = {}
        if body and 'Content-Type' not in self.session.headers: # Only set if not already set by specific methods (e.g., multipart)
            headers["Content-Type"] = "application/json"

        # Merge headers for this specific request
        req_headers = self.session.headers.copy()
        req_headers.update(headers)
        if "headers" in kwargs:
            req_headers.update(kwargs.pop("headers"))

        self.logger.debug(f"{method} {url} with headers: {req_headers}")
        
        resp = self.session.request(
            method=method,
            url=url,
            data=body,
            headers=req_headers,
            **kwargs
        )
        resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return resp

    def execute_command(self, command: Union[str, List[str]], timeout: Optional[float] = None) -> str:
        """
        Execute a shell command.
        
        Args:
            command: The command to execute, either as a single string or a list of arguments.
            timeout: Optional timeout for the command execution in seconds.
        Returns:
            str: The stdout of the executed command.
        Raises:
            CommandExecutionError: If the command returns a non-zero exit code.
        """
        timeout_value = timeout if timeout is not None else 60.0 # Default to 60s
        timeout_str = f"{timeout_value}s"

        cmd_list = shlex.split(command, posix=True) if isinstance(command, str) else command

        payload = {
            "command": cmd_list,
            "timeout": timeout_str
        }
        body = json.dumps(payload).encode('utf-8')
        
        # Add a buffer to the read timeout to allow PicoD to return the timeout response
        read_timeout = timeout_value + 5.0 # Give PicoD a bit more time to respond with timeout info
        
        resp = self._request("POST", "/api/execute", body=body, timeout=read_timeout)
        result = resp.json()

        if result.get("exit_code") != 0:
             raise CommandExecutionError(
                 exit_code=result.get("exit_code"),
                 stderr=result.get("stderr"),
                 command=command
             )
        
        return result.get("stdout", "")

    def run_code(self, language: str, code: str, timeout: Optional[float] = None) -> str:
        """
        Execute a code snippet in the remote environment.

        This method supports running code in various languages (e.g., Python, Bash).
        The execution context is managed by the remote PicoD instance.

        Args:
            language: The programming language of the code (e.g., "python", "bash").
            code: The actual code snippet to execute.
            timeout: Optional. The maximum time (in seconds) to wait for the code
                     execution to complete. If not provided, a default timeout applies.

        Returns:
            The standard output (stdout) generated by the code execution.
        """
        lang = language.lower()
        
        # Use file-based execution to avoid shell quoting issues and length limits
        # and ensure consistent behavior across PicoD executions.
        if lang in ["python", "py", "python3"]:
            filename = f"script_{int(time.time() * 1000)}.py"
            self.write_file(code, filename)
            cmd = ["python3", filename]
        elif lang in ["bash", "sh"]:
            filename = f"script_{int(time.time() * 1000)}.sh"
            self.write_file(code, filename)
            cmd = ["bash", filename]
        else:
            raise ValueError(f"Unsupported language: {language}")
            
        return self.execute_command(cmd, timeout)

    def write_file(self, content: str, remote_path: str, mode: str = "0644") -> None:
        """
        Write content to a file in the remote environment.

        Args:
            content: The string content to write to the file.
            remote_path: The destination path of the file in the remote environment.
            mode: File permissions in octal string format (e.g., "0644").
        """
        content_bytes = content.encode('utf-8')
        content_b64 = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {
            "path": remote_path,
            "content": content_b64,
            "mode": mode
        }
        body = json.dumps(payload).encode('utf-8')
        
        self._request("POST", "/api/files", body=body)

    def upload_file(self, local_path: str, remote_path: str, mode: str = "0644") -> None:
        """
        Upload a local file to the remote environment using multipart/form-data.

        Args:
            local_path: The path to the file on the local filesystem.
            remote_path: The destination path of the file in the remote environment.
            mode: File permissions in octal string format (e.g., "0644").
        Raises:
            FileNotFoundError: If the local file does not exist.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")
            
        with open(local_path, 'rb') as f:
            files = {'file': f}
            data = {'path': remote_path, 'mode': mode}
            
            # Use requests.Session directly for multipart to handle content-type header correctly
            url = f"{self.picod_url}/api/files"
            
            self.logger.debug(f"Uploading file {local_path} to {remote_path}")
            
            # The Authorization header is already set on self.session
            resp = self.session.post(url, files=files, data=data, timeout=60.0)
            resp.raise_for_status()

    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        Download a file from the remote environment to the local filesystem.

        Args:
            remote_path: The path to the file in the remote environment.
            local_path: The destination path on the local filesystem to save the file.
        """
        clean_path = remote_path.lstrip("/")
        resp = self._request("GET", f"/api/files/{clean_path}", stream=True)
        
        if os.path.dirname(local_path):
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        self.logger.info(f"Downloaded '{remote_path}' to '{local_path}'.")


    def list_files(self, path: str = ".") -> List[Dict[str, Any]]:
        """
        List files and directories in a specified path in the remote environment.

        Args:
            path: The directory path to list. Defaults to ".".
        Returns:
            A list of dictionaries, where each dictionary represents a file or directory
            with keys like 'name', 'size', 'mode', 'is_dir', 'modified'.
        """
        resp = self._request("GET", "/api/files", params={"path": path})
        return resp.json().get("files", [])
