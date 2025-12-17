import os
import time
import subprocess
import requests
import logging
import base64
import json
from pathlib import Path

from agentcube.code_interpreter import CodeInterpreterClient, AUTH_TOKEN
from agentcube.exceptions import CommandExecutionError

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sdk_e2e_test")

# --- Constants ---
# Assuming picod docker image is available
PICO_IMAGE_NAME = "light-picod:latest" # You might need to build this image if not available
CONTAINER_NAME = "picod_e2e_test_direct"
HOST_PORT = 8080
PICO_URL = f"http://localhost:{HOST_PORT}"

# --- Helper Functions ---

def start_picod_container():
    """Start the PicoD docker container."""
    logger.info(f"Starting Docker container {CONTAINER_NAME}...")
    
    # Remove existing if any
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    
    cmd = [
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{HOST_PORT}:8080",
        PICO_IMAGE_NAME # Assuming the image is built with the new PicoD server logic
    ]
    
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start container: {result.stderr}")
        
    # Wait for health check
    url = f"{PICO_URL}/health"
    retries = 20 # Increased retries
    for i in range(retries):
        try:
            resp = requests.get(url, timeout=1)
            if resp.status_code == 200:
                logger.info("PicoD is up and running!")
                return
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.debug(f"Health check attempt {i+1} failed: {e}")
        logger.info("Waiting for PicoD...")
        time.sleep(1)
        
    raise RuntimeError("PicoD failed to start or is unhealthy")

def stop_picod_container():
    """Stop the Docker container."""
    logger.info(f"Stopping container {CONTAINER_NAME}...")
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

# --- Main Test ---

def main():
    # Ensure local_test_artifacts directory exists
    Path("local_test_artifacts").mkdir(exist_ok=True)
    
    try:
        # 1. Start PicoD Container
        start_picod_container()
        
        # 2. Initialize SDK Client
        logger.info("Initializing CodeInterpreterClient for direct PicoD communication...")
        client = CodeInterpreterClient(
            picod_url=PICO_URL,
            verbose=True
        )
        
        # 3. Run Tests
        with client: # Use context manager to ensure session closure
            logger.info(">>> TEST: Execute Command (echo)")
            output = client.execute_command("echo 'Hello SDK'")
            print(f"Output: {output.strip()}")
            assert output.strip() == "Hello SDK"

            logger.info(">>> TEST: Execute Command with List Arguments")
            output_list_cmd = client.execute_command(["echo", "Hello from list args"])
            print(f"Output (list args): {output_list_cmd.strip()}")
            assert output_list_cmd.strip() == "Hello from list args"
            
            logger.info(">>> TEST: Run Python Code")
            code = "print(10 + 20)"
            output = client.run_code("python", code)
            print(f"Output: {output.strip()}")
            assert output.strip() == "30"
            
            logger.info(">>> TEST: File Upload & Download (write_file and download_file)")
            test_content = "This is a test file for PicoD."
            remote_filename = "test.txt"
            local_download_path = "local_test_artifacts/downloaded_test.txt"
            
            client.write_file(test_content, remote_filename)
            
            # Verify PicoD has the file by executing cat
            output_cat = client.execute_command(f"cat {remote_filename}")
            assert output_cat.strip() == test_content
            
            client.download_file(remote_filename, local_download_path)
            with open(local_download_path, "r") as f:
                content = f.read()
            assert content == test_content
            logger.info(f"Verified downloaded file content: {content}")

            logger.info(">>> TEST: File Upload (Multipart)")
            local_multipart_path = "local_test_artifacts/local_multipart.txt"
            remote_multipart_path = "remote_multipart.txt"
            multipart_content = "This is multipart content for PicoD."
            with open(local_multipart_path, "w") as f:
                f.write(multipart_content)
            
            try:
                client.upload_file(local_multipart_path, remote_multipart_path)
                
                # Verify upload with cat
                output_multipart_cat = client.execute_command(f"cat {remote_multipart_path}")
                assert output_multipart_cat.strip() == multipart_content
                logger.info(f"Verified multipart uploaded file content: {output_multipart_cat.strip()}")
            finally:
                 if os.path.exists(local_multipart_path):
                     os.remove(local_multipart_path)

            logger.info(">>> TEST: List Files")
            files = client.list_files(".")
            filenames = [f['name'] for f in files]
            logger.info(f"Files found: {filenames}")
            assert remote_filename in filenames
            assert remote_multipart_path in filenames
            
            # Verify file info structure
            test_file_info = next(f for f in files if f['name'] == remote_filename)
            assert test_file_info['size'] > 0
            assert not test_file_info['is_dir']
            logger.info(f"File info for {remote_filename}: {test_file_info}")

            logger.info(">>> TEST: Command Failure")
            try:
                client.execute_command("ls /nonexistent_directory_for_test")
                assert False, "Command should have failed"
            except CommandExecutionError as e:
                logger.info(f"Caught expected error: {e}")
                assert e.exit_code != 0
            except Exception as e:
                assert False, f"Caught unexpected exception type: {type(e)}"
                
            logger.info(">>> TEST: Timeout")
            # Should pass with sufficient timeout
            output_sleep_short = client.execute_command("sleep 0.1", timeout=1.0)
            assert output_sleep_short.strip() == "" # sleep produces no stdout by default
            logger.info("Short sleep command successful.")
            
            try:
                 # Should fail with short timeout
                 client.execute_command("sleep 3", timeout=0.5)
                 assert False, "Command should have timed out"
            except CommandExecutionError as e:
                 logger.info(f"Caught expected timeout error: {e}")
                 # PicoD returns exit code 124 for timeout
                 assert e.exit_code == 124
            except Exception as e:
                assert False, f"Caught unexpected exception type: {type(e)} - {e}"

            logger.info(">>> TEST: Unauthenticated Access via direct requests (should fail)")
            unauth_headers = {"Authorization": "Bearer invalid-token"}
            resp_unauth = requests.post(
                f"{PICO_URL}/api/execute", 
                headers=unauth_headers, 
                json={"command": ["echo", "unauthorized"]},
                timeout=5
            )
            assert resp_unauth.status_code == 401
            assert "Invalid token" in resp_unauth.json().get("error", "")
            logger.info(f"Unauthenticated access attempt resulted in {resp_unauth.status_code} (Expected 401).")


            logger.info(">>> ALL TESTS PASSED SUCCESSFULLY! <<<")
        
    except Exception as e:
        logger.error(f"Test Failed: {e}", exc_info=True)
        # Print container logs on failure
        logs = subprocess.run(["docker", "logs", CONTAINER_NAME], capture_output=True, text=True)
        print("--- Container Logs ---")
        print(logs.stderr)
        print(logs.stdout)
        raise
        
    finally:
        # Cleanup
        stop_picod_container()
        if os.path.exists(local_download_path):
            os.remove(local_download_path)
        # Clean up the local_test_artifacts directory
        if Path("local_test_artifacts").exists():
            for f in Path("local_test_artifacts").iterdir():
                os.remove(f)
            Path("local_test_artifacts").rmdir()

if __name__ == "__main__":
    main()
