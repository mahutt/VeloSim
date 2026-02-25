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

import os
import sys
import gdown
from grafana_logging.logger import get_logger

logger = get_logger(__name__)


def download_template(level, file_id) -> bool:
    """
    Securely downloads the file_id template from the drive if it does not exist already.
    Resumes download if was previously interrupted.

    Args:
        file_id: ID of shared google drive file
        local_path: Path of local expected template

    Returns:
        True if file successfully downloaded or already exists. Otherwise, False
    """
    url = f"https://drive.google.com/uc?id={file_id}"
    local_path = f"sim/traffic/traffic_datasets/{level}.csv"
    temp_path = local_path + ".tmp"

    # Check if local file exists
    if os.path.exists(local_path):
        print(f"Local file for {level} exists. Skipping download.")
        return True

    print(f"Starting/Resuming download for {local_path}...")

    try:
        # gdown handles the virus warning and returns the path of the downloaded file
        downloaded_file = gdown.download(url, temp_path, quiet=False, resume=True)

        if downloaded_file:
            # Only rename if the download finished successfully
            os.rename(temp_path, local_path)
            print(f"Successfully downloaded and verified: {local_path}")
            return True

    except Exception as e:
        logger.error("ERROR: Automated download failed or the file is missing.")
        logger.error(f"Failed to download {level} traffic template: {e}")
        logger.error(
            "If the process was interrupted, run the script again to resume from where it left off."
        )

    return False


try:
    templates = {
        "high_congestion": "1E8W64tetwsqs6G5jUwbS7i22Y9sD7T51",
        "medium_congestion": "1n9RrYPwaKYTuJu55I7wRVZsE1wzjqyW7",
        "low_congestion": "1-iGTP1bzEaesItxF-SgXm8820DRs4u1M",
    }

    for level, file_id in templates.items():
        if not download_template(level, file_id):
            sys.exit(1)

except Exception as e:
    logger.error(f"Failed to retrieve a template csv: {e}")
    sys.exit(1)
