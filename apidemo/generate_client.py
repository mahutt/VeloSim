#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
"""

Generate VeloSim Python client from OpenAPI specification.

This script fetches the OpenAPI spec from a running VeloSim instance
and generates a type-safe Python client using openapi-python-client.
"""

import sys
import shutil
import subprocess
from pathlib import Path
import requests

DEFAULT_API_URL = "http://localhost:8000"


def fetch_openapi_spec(
    api_url: str, output_path: Path, use_local: bool = False
) -> bool:
    """Fetch OpenAPI specification from VeloSim API or use local backup.

    Args:
        api_url: Base URL of VeloSim API
        output_path: Path to save the spec
        use_local: If True, use the committed backup instead of fetching

    Returns:
        True if successful, False otherwise
    """
    # Check for committed backup first
    backup_path = Path(__file__).parent / "openapi.json"

    if use_local:
        if backup_path.exists():
            print(f"Using local OpenAPI spec backup: {backup_path}")
            if output_path != backup_path:
                import shutil

                shutil.copy(backup_path, output_path)
            return True
        else:
            print("✗ No local backup found")
            return False

    spec_url = f"{api_url}/openapi.json"

    try:
        print(f"Fetching OpenAPI spec from {spec_url}...")
        response = requests.get(spec_url, timeout=10.0)
        response.raise_for_status()

        # Save spec to file
        output_path.write_text(response.text)
        print(f"✓ Saved OpenAPI spec to {output_path}")
        return True

    except requests.ConnectionError:
        print(f"✗ Could not connect to {api_url}")
        print("API not reachable (production deployments have OpenAPI disabled)")

        # Try local backup as fallback
        if backup_path.exists():
            print(f"Using local backup: {backup_path}")
            if output_path != backup_path:
                import shutil

                shutil.copy(backup_path, output_path)
            return True
        else:
            print("✗ No local backup available")
            return False

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            print("✗ OpenAPI endpoint not available (production mode)")

            # Try local backup
            if backup_path.exists():
                print(f"Using local backup: {backup_path}")
                if output_path != backup_path:
                    import shutil

                    shutil.copy(backup_path, output_path)
                return True
            else:
                print("✗ No local backup available")
                return False
        else:
            print(f"✗ HTTP error: {e.response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error fetching spec: {e}")
        return False


def generate_client(spec_path: Path, output_dir: Path) -> bool:
    """Generate Python client using openapi-python-client.

    Args:
        spec_path: Path to OpenAPI spec file
        output_dir: Directory where client should be generated

    Returns:
        True if successful, False otherwise
    """
    try:
        # Remove existing client if present
        if output_dir.exists():
            print(f"Removing existing client at {output_dir}")
            shutil.rmtree(output_dir)

        print("Generating Python client...")

        # Build command
        cmd = [
            "openapi-python-client",
            "generate",
            "--path",
            str(spec_path),
        ]

        # Add config if it exists
        config_path = Path(__file__).parent / "client_config.yaml"
        if config_path.exists():
            cmd.extend(["--config", str(config_path)])

        # Run openapi-python-client
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print("✗ Client generation failed!")
            print(result.stderr)
            return False

        # The generated client will be in a subfolder, move it to output_dir
        generated_path = Path("velosim-backend-api-client")
        if generated_path.exists():
            generated_path.rename(output_dir)
            print(f"✓ Client generated at {output_dir}")
        else:
            print("Client generated but not found at expected path")
            print(f"Check for directory: {generated_path}")

        return True

    except FileNotFoundError:
        print("✗ openapi-python-client not found!")
        print("Install it with: pip install openapi-python-client")
        return False
    except Exception as e:
        print(f"✗ Error generating client: {e}")
        return False


def main():
    """Main entry point."""
    # Check for --local flag
    use_local = "--local" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--local"]

    # Get API URL from args or use default
    api_url = args[0] if args else DEFAULT_API_URL

    # Setup paths
    script_dir = Path(__file__).parent
    spec_path = script_dir / "openapi.json"
    client_dir = script_dir / "velosim_client"

    print("VeloSim Python Client Generator")
    print("=" * 40)
    print()

    # Fetch spec (with local fallback)
    if not fetch_openapi_spec(api_url, spec_path, use_local=use_local):
        sys.exit(1)

    print()

    # Generate client
    if not generate_client(spec_path, client_dir):
        sys.exit(1)

    print()
    print("✓ Client generation complete!")
    print()
    print("You can now use the client:")
    print("  from velosim_client import Client")
    print("  client = Client(base_url='http://localhost:8000')")
    print()


if __name__ == "__main__":
    main()
