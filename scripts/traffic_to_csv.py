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
import time
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from sim.map.MapController import MapController

#def traffic_to_csv(map_controller: MapController) -> None:

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Find the project root (where .env is located)
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}")
except ImportError:
    print(
        "Warning: python-dotenv not installed. "
        "Install with: pip install python-dotenv"
    )
    print("  Environment variables from .env file will not be loaded automatically.")

try:
    # =========================================================================
    # Initialize MapController with Traffic Support
    # =========================================================================
    print("\nInitializing MapController with traffic support...")

    # Get OSRM URL from environment variable
    osrm_url = os.getenv("OSRM_URL")
    local_url = os.getenv("OSRM_LOCAL_URL")
    public_url = os.getenv("OSRM_PUBLIC_URL")

    if osrm_url:
        print(f"Using specified OSRM server: {osrm_url}")
        map_controller = MapController(osrm_url=osrm_url, enable_traffic=True)
    elif local_url:
        try:
            print(f"Trying local OSRM server at {local_url}...")
            map_controller = MapController(osrm_url=local_url, enable_traffic=True)
            print("Connected to local OSRM server")
        except Exception as e:
            print(f"  Local server not available: {e}")
            if public_url:
                print(f"  Falling back to public OSRM server at {public_url}...")
                map_controller = MapController(osrm_url=public_url, enable_traffic=True)
                print("Connected to public OSRM server")
            else:
                raise ConnectionError(
                    "No OSRM server available. Please set OSRM_URL, "
                    "OSRM_LOCAL_URL, or OSRM_PUBLIC_URL environment variable."
                )
    elif public_url:
        print(f"Using public OSRM server at {public_url}...")
        map_controller = MapController(osrm_url=public_url, enable_traffic=True)
        print("Connected to public OSRM server")
    else:
        raise ConnectionError(
            "No OSRM server configured. Please set one of:\n"
            "  - OSRM_URL (primary server)\n"
            "  - OSRM_LOCAL_URL (local server)\n"
            "  - OSRM_PUBLIC_URL (public/fallback server)"
        )

    print("MapController initialized with traffic management enabled")

    print(f'starting process...')
    start_time = time.perf_counter()
    trips = pd.read_csv("sim/traffic/montreal_data/trips2019.csv")
    read_file = time.perf_counter()
    print(f'time to read file: {read_file - start_time}')

    # filter dataframe
    # removes unnecessary columns, trips with short segments
    trips = trips.drop(columns=['SrcDetectorId', 'DestDetectorId'])
    trips = trips[trips['PathDistance_m'] >= 100]
    filter_time = time.perf_counter()
    print(f'time to filter dataframe: {filter_time - read_file}')

    # get average speeds for each segment at every hour
    trips['TripStart_dt'] = pd.to_datetime(trips['TripStart_dt'])
    trips['Hour'] = trips['TripStart_dt'].dt.hour
    #trips['DayType'] = trips['TripStart_dt'].dt.dayofweek.apply(lambda x: 'weekend' if x >= 5 else 'weekday')

    #hourly_speeds = trips.groupby(['LinkId', 'hour', 'DayType'])['Speed_kmh'].mean().reset_index()
    hourly_speeds = trips.groupby(['LinkId', 'Hour'])['Speed_kmh'].mean().reset_index()
    hourly_speeds.rename(columns={'Speed_kmh': 'AvgSpeedHour'}, inplace=True)
    speed_time = time.perf_counter()
    print(f'time to get average speeds by hour: {speed_time - filter_time}')

    """
    # calculate free flow speed for each unique segment by LinkId using 95th percentile
    baselines = trips.groupby('LinkId')['Speed_kmh'].quantile(0.95).reset_index()
    baselines.columns = ['LinkId', 'FreeFlowSpeed']
    free_speed = time.perf_counter()
    print(f'time to calc all free flow speeds: {free_speed - filter_time}')

    # merge baseline back to trips data
    trips = trips.merge(baselines, on='LinkId')
    merge_time = time.perf_counter()
    print(f'time to merge back: {merge_time - free_speed}')

    # define the congestion ratio (current speed/free flow speed)
    trips['speed_ratio'] = trips['Speed_kmh'] / trips['FreeFlowSpeed']
    """

    # calculate free flow speeds for each segment by max hourly avg speed
    baselines = hourly_speeds.groupby('LinkId')['AvgSpeedHour'].max().reset_index()
    baselines.rename(columns={'AvgSpeedHour': 'FreeFlowSpeed'}, inplace=True)
    free_speed = time.perf_counter()
    print(f'time to calc all free flow speeds: {free_speed - speed_time}')

    # merge baseline back with hourly_speeds dataframe
    final_df = hourly_speeds.merge(baselines, on='LinkId')
    merge_time = time.perf_counter()
    print(f'time to merge back: {merge_time - free_speed}')

    # define the congestion ratio (current speed/free flow speed)
    final_df['speed_ratio'] = final_df['AvgSpeedHour'] / final_df['FreeFlowSpeed']

    # determine traffic levels
    def get_traffic_level(ratio: float) -> str:
        """Returns traffic level according to provided ratio"""
        if ratio >= 0.9:
            return 'free_flow'
        elif 0.7 <= ratio < 0.9:
            return 'light'
        elif 0.45 <= ratio < 0.7:
            return 'moderate'
        elif 0.25 <= ratio < 0.45:
            return 'heavy'
        else:
            return 'severe'

    final_df['level'] = final_df['speed_ratio'].apply(get_traffic_level)
    lvl_time = time.perf_counter()
    print(f'time to determine traffic: {lvl_time - merge_time}')

    segments = pd.read_excel("sim/traffic/montreal_data/bornes.xlsx")
    subset_segments = segments[['LinkId', 'SrcLatitude', 'SrcLongitude', 'DestLatitude', 'DestLongitude']]
    read_segment = time.perf_counter()
    print(f'time to read segments and filter file: {read_segment - lvl_time}')

    #traffic_levels = final_df['level'].unique()
    traffic_hours = final_df['Hour'].unique()
    #for lvl in traffic_levels:
    for hour in traffic_hours:
        lvl_start = time.perf_counter()
        #lvl_dataframe = final_df[final_df['level'] == lvl]
        hour_dataframe = final_df[final_df['Hour'] == hour]
        #subset_lvl = lvl_dataframe[['LinkId', 'Hour', 'AvgSpeedHour']]
        subset_hour = hour_dataframe[['LinkId', 'AvgSpeedHour', 'level']]
        mapped_data = pd.merge(subset_hour, subset_segments, on='LinkId')
        """
        filename = f"sim/traffic/traffic_datasets/hourly_traffic_{lvl}.csv"
        csv_contents.to_csv(filename, index=False)
        print(f'time to create csv {lvl}: {time.perf_counter() - lvl_start}')
        """

        tqdm.pandas()
        print("Matching Montreal segments to OSM nodes via OSRM...")
        mapped_data[['from_osm_id', 'to_osm_id']] = mapped_data.progress_apply(map_controller.get_nodes_from_edge_points, axis=1)
        mapping_id_time = time.perf_counter()
        print(f'time to map ids: {mapping_id_time - lvl_start}')

        # remove values missing node ids and ensure nodes are type int
        mapped_data = mapped_data.dropna(subset=['from_osm_id', 'to_osm_id'])
        mapped_data['from_osm_id'] = mapped_data['from_osm_id'].astype(int)
        mapped_data['to_osm_id'] = mapped_data['to_osm_id'].astype(int)
        fix_time = time.perf_counter()
        print(f'time to make fixes: {fix_time - mapping_id_time}')

        # create traffic csv with specific columns
        final_output = mapped_data[['from_osm_id', 'to_osm_id', 'AvgSpeedHour', 'level']]
        final_output.columns = ['from_osm_id', 'to_osm_id', 'edge_speed_in_km_h', 'congestion_level']
        filename = f"sim/traffic/traffic_datasets/traffic_{hour}h.csv"
        file_path = Path(filename)
        file_path.parent.mkdir(exist_ok=True) # create traffic_datasets if does not exist
        final_output.to_csv(filename, index=False)
        print(f'time to make {hour}h csv: {time.perf_counter() - fix_time}')

        """
        speeds = trips[['LinkId', 'Speed_kmh']].copy()
        #avg_speeds = trips.groupby('LinkId')['Speed_kmh'].mean().reset_index()
        speed_time = time.perf_counter()
        print(f'time for getting speeds: {speed_time - start_time}')

        # merge trips and segments files to include start and end coordinates
        # of segments with their speeds
        segments = pd.read_excel("C:/Users/sumer/Downloads/bornes.xlsx")
        mapped_data = pd.merge(speeds, segments, on='LinkId')
        datagram_time = time.perf_counter()
        print(f'time to make datagram: {datagram_time - speed_time}')

        first_row_series = mapped_data.iloc[0]
        print(first_row_series)

        """
        """
            tqdm.pandas()
            print("Matching Montreal segments to OSM nodes via OSRM...")
            mapped_data[['from_osm_id', 'to_osm_id']] = mapped_data.progress_apply(map_controller.osrm.coordinates_to_edge, axis=1)
            mapping_id_time = time.perf_counter()
            print(f'time to map ids: {mapping_id_time - datagram_time}')

            # remove values missing node ids and ensure nodes are type int
            mapped_data = mapped_data.dropna(subset=['from_osm_id', 'to_osm_id'])
            mapped_data['from_osm_id'] = mapped_data['from_osm_id'].astype(int)
            mapped_data['to_osm_id'] = mapped_data['to_osm_id'].astype(int)
            fix_time = time.perf_counter()
            print(f'time to make fixes: {fix_time - mapping_id_time}')

            # create traffic csv with specific columns
            final_output = mapped_data[['from_osm_id', 'to_osm_id', 'Speed_kmh']]
            final_output.columns = ['from_osm_id', 'to_osm_id', 'edge_speed_in_km_h']
            final_output.to_csv('montreal_osm_traffic.csv', index=False)
            print(f'time to make csv: {time.perf_counter() - fix_time}')
        """
except Exception as e:
    print(e)
