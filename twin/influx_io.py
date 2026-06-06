import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_influx_config():
    return {
        "url": os.environ.get("INFLUXDB_URL", "http://localhost:8086"),
        "token": os.environ.get("INFLUXDB_TOKEN", "demo-token"),
        "org": os.environ.get("INFLUXDB_ORG", "demo-org"),
        "bucket": os.environ.get("INFLUXDB_BUCKET", "demo-bucket"),
    }

def write_state(state):
    """Write engine state to InfluxDB."""
    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS
        
        cfg = get_influx_config()
        client = InfluxDBClient(url=cfg["url"], token=cfg["token"], org=cfg["org"])
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        point = Point("engine_telemetry") \
            .tag("unit_id", str(state["unit_id"])) \
            .field("cycle", state["cycle"]) \
            .field("RUL", state["RUL"])
            
        for k, v in state.get("sensors", {}).items():
            point = point.field(k, v)
            
        for k, v in state.get("settings", {}).items():
            point = point.field(k, v)
            
        point = point.time(datetime.utcnow())
        write_api.write(bucket=cfg["bucket"], org=cfg["org"], record=point)
        client.close()
        return True
    except Exception as e:
        logger.warning(f"Failed to write InfluxDB state: {e}")
        return False

def query_recent(unit_id, limit=200):
    """Query recent points from InfluxDB and return pandas DataFrame."""
    try:
        from influxdb_client import InfluxDBClient
        import pandas as pd
        
        cfg = get_influx_config()
        client = InfluxDBClient(url=cfg["url"], token=cfg["token"], org=cfg["org"])
        query_api = client.query_api()
        
        query = f'''
        from(bucket: "{cfg['bucket']}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "engine_telemetry")
          |> filter(fn: (r) => r["unit_id"] == "{unit_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["cycle"], desc: true)
          |> limit(n: {limit})
        '''
        
        df = query_api.query_data_frame(query, org=cfg["org"])
        client.close()
        
        if isinstance(df, list):
            if len(df) == 0:
                return None
            df = df[0]
            
        if df is None or df.empty:
            return None
            
        # Sort back to ascending for charting
        df = df.sort_values("cycle").reset_index(drop=True)
        return df
    except Exception as e:
        logger.warning(f"Failed to query InfluxDB: {e}")
        return None
