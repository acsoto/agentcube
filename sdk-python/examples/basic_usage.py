from agentcube import CodeInterpreterClient
import os

def main():
    """
    This example demonstrates the basic usage of the simplified AgentCube Python SDK.
    It requires a running PicoD instance.
    
    Ensure the following environment variable is set before running:
    - PICOD_URL: URL of the PicoD service (e.g., "http://localhost:8080")
    """
    
    picod_url = os.getenv("PICOD_URL")
    if not picod_url:
        print("Error: PICOD_URL environment variable is not set.")
        print("Please set it to the URL of your PicoD instance (e.g., 'http://localhost:8080').")
        return

    print(f"Initializing AgentCube Client for PicoD at: {picod_url}...")
    
    try:
        # Using context manager ensures the session is closed after use
        with CodeInterpreterClient(picod_url=picod_url, verbose=True) as client:
            print("Client initialized successfully!")

            # 1. Execute a simple Shell Command
            print("\n--- 1. Shell Command: whoami ---")
            output = client.execute_command("whoami")
            print(f"Result: {output.strip()}")

            print("\n--- 2. Shell Command: Check OS release ---")
            output = client.execute_command("cat /etc/os-release")
            print(f"Result:\n{output.strip()}")

            # 2. Execute Python Code
            print("\n--- 3. Python Code: Calculate Pi ---")
            code = """
                import math
                print(f"Pi is approximately {math.pi:.6f}")
            """
            output = client.run_code("python", code)
            print(f"Result: {output.strip()}")

            # 3. File Operations
            print("\n--- 4. File Operations ---")
            
            # Write a file to the remote sandbox
            remote_filename = "hello_agentcube.txt"
            content = "Hello from AgentCube SDK Example!"
            print(f"Writing to '{remote_filename}'...")
            client.write_file(content, remote_filename)
            
            # Verify file creation by listing files
            print("Listing files in current directory...")
            files = client.list_files(".")
            for f in files:
                print(f" - {f['name']} ({f['size']} bytes)")
                
            # Read the file back (using cat for simplicity)
            print(f"Reading '{remote_filename}' content...")
            output = client.execute_command(f"cat {remote_filename}")
            print(f"File content: {output.strip()}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        # Note: If an exception occurs within the 'with' block, 
        # the __exit__ method is still called, ensuring cleanup.

if __name__ == "__main__":
    main()