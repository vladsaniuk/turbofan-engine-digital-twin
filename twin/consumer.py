import json
import logging
from twin.mqtt_io import start_subscriber
from twin.influx_io import write_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("twin.consumer")

def handle_message(payload):
    """Process incoming MQTT payload and write to InfluxDB."""
    try:
        state = json.loads(payload)
        unit_id = state.get("unit_id", "unknown")
        cycle = state.get("cycle", "unknown")
        
        ok = write_state(state)
        if ok:
            logger.info(f"wrote cycle {cycle} for unit {unit_id} → InfluxDB")
        else:
            logger.error(f"failed to write cycle {cycle} for unit {unit_id} → InfluxDB")
            
    except Exception as e:
        logger.error(f"Failed to process message: {e}")

if __name__ == "__main__":
    logger.info("Starting telemetry consumer...")
    try:
        start_subscriber(handle_message)
    except KeyboardInterrupt:
        logger.info("Exiting consumer...")
