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
import time
import gdown
import requests
from pathlib import Path
import pandas as pd
from tqdm import tqdm

def download_dataset(file_id, local_path) -> bool:
    """
    Securely downloads the file_id dataset from the drive if it does not exist already.
    Resumes download if was previously interrupted.

    Args:
        file_id: ID of shared google drive file
        local_path: Path of local expected dataset

    Returns:
        True if file successfully downloaded or already exists. Otherwise, False
    """
    url = f'https://drive.google.com/uc?id={file_id}'
    temp_path = local_path + ".tmp"

    # Check if local file exists and compare size
    if os.path.exists(local_path):
        print("Local file exists. Skipping download.")
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
        print(f"Download failed or was interrupted: {e}")
        print("Run the script again to resume from where it left off.")

    return False

try:
    os.makedirs("sim/traffic/montreal_data", exist_ok=True)
    traffic_file_id = 'REDACTED'
    url = f'https://drive.google.com/uc?export=download&id={traffic_file_id}'
    output = "sim/traffic/montreal_data/traffic2019.csv"

    # takes about a minute if the file does not already exist
    if not download_dataset(traffic_file_id, output):
        print("Script was interrupted. Please verify that the drive is still available and rerun the script.")
        sys.exit()

    filtered_chunks = []
    for chunk in tqdm(pd.read_csv(output, chunksize=50000), desc="Loading Montreal Dataset"):
        chunk = chunk.drop(columns=["SrcDetectorId", "DestDetectorId"])
        filtered_chunks.append(chunk)
    trips = pd.concat(filtered_chunks)

    # filter dataframe
    # removes unnecessary columns, trips with short segments
    start_time = time.perf_counter()
    trips = trips[trips["PathDistance_m"] >= 100]
    filter_time = time.perf_counter()
    print(f"time to filter dataframe: {filter_time - start_time}")

    # convert TripStart_dt to datetime format
    # includes progress bar as slower process
    tqdm.pandas(desc="Preparing Dataframe")
    trips["TripStart_dt"] = pd.to_datetime(trips["TripStart_dt"]).progress_apply(
        lambda x: x
    )

    # calculate free flow speeds for each segment by LinkId using 85th percentile
    speed_time = time.perf_counter()
    baselines = trips.groupby("LinkId")["Speed_kmh"].quantile(0.85).reset_index()
    baselines.columns = ["LinkId", "free_flow_speed"]
    free_speed = time.perf_counter()
    print(f"time to calc all free flow speeds: {free_speed - speed_time}")

    # merge baselines back with trips dataframe
    df = trips.merge(baselines, on="LinkId")
    merge_time = time.perf_counter()
    print(f"time to merge back: {merge_time - free_speed}")

    # define the congestion (speed) ratio (current speed/free flow speed)
    # caps ratio values to 1 max
    df["speed_ratio"] = df["Speed_kmh"] / df["free_flow_speed"]
    df["speed_ratio"] = df["speed_ratio"].clip(upper=1)

    # filter for weekdays to exclude weekend traffic state
    start_filter = time.perf_counter()
    df["day_of_week"] = df["TripStart_dt"].dt.day_of_week
    weekday_df = df[df["day_of_week"] < 5].copy()  # 0-5 -> Monday to Friday
    filter_time = time.perf_counter()
    print(f"time to filter to weekdays only: {filter_time - start_filter}")

    # create a time of day column with intervals of 5 minutes
    # rounds 08:07 down to 08:05, 08:22 down to 08:20, etc.
    weekday_df["time_window"] = weekday_df["TripStart_dt"].dt.floor("5min").dt.time

    # create a typical day dataframe
    typical_day = (
        weekday_df.groupby(["LinkId", "time_window"])
        .agg(typical_speed_ratio=("speed_ratio", "mean"))
        .reset_index()
    )
    typical_day = typical_day.sort_values(["LinkId", "time_window"])
    typical_time = time.perf_counter()
    print(f"time to get typical day: {typical_time - filter_time}")

    # get the speed ratio difference between the current row and the previous one
    typical_day["ratio_diff"] = (
        typical_day.groupby("LinkId")["typical_speed_ratio"].diff().abs()
    )

    # determine when a state changes. State conditions:
    # 1. Difference in ratio is >= 0.05
    # 2. Change in segment by LinkId
    typical_day["state_change"] = (typical_day["ratio_diff"] >= 0.05) | (
        typical_day["LinkId"] != typical_day["LinkId"].shift()
    )
    state_change_time = time.perf_counter()
    print(f"time to determine all state changes: {state_change_time - typical_time}")

    # create a unique ID for each event on each segment and group them with
    # their start and end time, as well as their average speed ratio
    typical_day["event_id"] = typical_day["state_change"].cumsum()
    final_df = (
        typical_day.groupby(["event_id", "LinkId"])
        .agg(
            start_time=("time_window", "min"),
            avg_speed_ratio=("typical_speed_ratio", "mean"),
            window_count=("time_window", "count"),
        )
        .reset_index()
    )
    grouping_time = time.perf_counter()
    print(f"time to group events: {grouping_time - state_change_time}")

    # calculate duration of an event
    # if 3 windows of 5 minute intervals -> 3 slots * 5 = 15 minutes * 60 sec
    final_df["event_duration"] = final_df["window_count"] * 5 * 60

    # get segment_key for all segments
    bornes_file_id = 'REDACTED'
    url = f'https://drive.google.com/uc?export=download&id={bornes_file_id}'
    segments = pd.read_excel("sim/traffic/montreal_data/bornes.xlsx")
    subset_segments = segments[
        ["LinkId", "SrcLatitude", "SrcLongitude", "DestLatitude", "DestLongitude"]
    ].copy()
    # use of zip is way faster than .apply for larger datasets
    subset_segments["segment_key"] = list(
        zip(
            zip(subset_segments["SrcLongitude"], subset_segments["SrcLatitude"]),
            zip(subset_segments["DestLongitude"], subset_segments["DestLatitude"]),
        )
    )
    final_subset = subset_segments[["LinkId", "segment_key"]]
    prepare_segment_key = time.perf_counter()
    print(
        f"time to read segments and get segment_keys: {prepare_segment_key - grouping_time}"
    )

    # merge both final dataframes by LinkId
    mapped_data = pd.merge(final_df, final_subset, on="LinkId")
    map_time = time.perf_counter()
    print(f"time to map both datasets: {map_time - prepare_segment_key}")

    # create traffic csv with specific columns
    # TYPE,start_time,segment_key,name,duration,weight
    traffic_type = "local_traffic"  # only one for now
    mapped_data["traffic_type"] = traffic_type
    mapped_data["name"] = ""
    final_output = mapped_data[
        [
            "traffic_type",
            "start_time",
            "segment_key",
            "name",
            "event_duration",
            "avg_speed_ratio",
        ]
    ]
    final_output.columns = [
        "traffic_type",
        "start_time",
        "segment_key",
        "name",
        "duration",
        "weight",
    ]

    filename = f"sim/traffic/traffic_datasets/traffic.csv"
    file_path = Path(filename)
    file_path.parent.mkdir(exist_ok=True)  # create traffic_datasets if does not exist
    final_output.to_csv(filename, index=False)
    print(f"time to make traffic csv: {time.perf_counter() - map_time}")

except Exception as e:
    print(e)
