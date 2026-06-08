import json
import logging

logger = logging.getLogger(__name__)

def publish_state(state, topic="twin/engine/telemetry", host="localhost", port=1883):
    """Publish engine state to MQTT broker."""
    try:
        import paho.mqtt.publish as publish
        
        payload = json.dumps(state)
        publish.single(topic, payload=payload, hostname=host, port=port)
        return True
    except Exception as e:
        logger.warning(f"Failed to publish MQTT state: {e}")
        return False

def start_subscriber(callback, topic="twin/engine/telemetry", host="localhost", port=1883):
    """Start blocking MQTT subscriber that invokes callback on message."""
    try:
        import paho.mqtt.client as mqtt
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"Connected to MQTT broker at {host}:{port}")
                client.subscribe(topic)
            else:
                logger.error(f"Failed to connect to MQTT broker, code {rc}")
                
        def on_message(client, userdata, msg):
            callback(msg.payload)
            
        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Loop forever with automatic reconnect
        client.connect(host, port)
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Subscriber stopped manually.")
    except Exception as e:
        logger.error(f"Subscriber failed: {e}")
