import simpy
from datetime import datetime

class MaintenanceCrew:
    def __init__(self, env):
        self.env = env
        self.crew = simpy.Resource(env, capacity=1)

def maintenance_process(env, crew, event_log):
    event_log.append(f"[{env.now:.1f}h] Maintenance request generated. Queuing for crew...")
    
    with crew.request() as req:
        yield req
        event_log.append(f"[{env.now:.1f}h] Crew acquired. Starting repair...")
        yield env.timeout(4.0)  # Fixed repair time (4 hours)
        event_log.append(f"[{env.now:.1f}h] Repair complete. Engine cleared for operation.")

def evaluate_maintenance(predicted_rul: float, threshold: float = 25) -> dict:
    """Run a short simpy model to evaluate the maintenance decision and queueing."""
    should_schedule = predicted_rul < threshold
    
    if not should_schedule:
        return {
            "schedule": False,
            "urgency": "Normal",
            "log": []
        }
        
    env = simpy.Environment()
    crew = MaintenanceCrew(env).crew
    event_log = []
    
    env.process(maintenance_process(env, crew, event_log))
    env.run(until=10) # Run until repair finishes (which takes ~4 hours)
    
    urgency = "Critical" if predicted_rul < (threshold / 2) else "High"
    
    return {
        "schedule": True,
        "urgency": urgency,
        "log": event_log
    }
