import json
import os
from core.event_bus import event_bus
from core.peterjones import get_logger
from core.config import MITCH_ROOT

logger = get_logger("resource_optimizer")

RESOURCE_OPTIMIZER_FILE = f"{MITCH_ROOT}/data/injections/resource_optimizer.json"
LOG_FILE = os.path.join(MITCH_ROOT, "logs", "innermono.log")

class ResourceOptimizer:
    def __init__(self):
        self.resource_settings = self.load_settings()

    def load_settings(self):
        if os.path.exists(RESOURCE_OPTIMIZER_FILE):
            with open(RESOURCE_OPTIMIZER_FILE, 'r') as file:
                return json.load(file)
        return {}

    def save_settings(self):
        with open(RESOURCE_OPTIMIZER_FILE, 'w') as file:
            json.dump(self.resource_settings, file)

    def optimize_resources(self, data):
        # Analyze system performance data and adjust resource settings
        metrics = data.get('metrics', {})
        cpu_usage = metrics.get('cpu_usage', 0)
        memory_usage = metrics.get('memory_usage', 0)
        
        if cpu_usage > 80:
            self.resource_settings['cpu_limit'] = min(self.resource_settings.get('cpu_limit', 100), 90)
        else:
            self.resource_settings['cpu_limit'] = min(self.resource_settings.get('cpu_limit', 100) + 5, 100)
        
        if memory_usage > 80:
            self.resource_settings['memory_limit'] = min(self.resource_settings.get('memory_limit', 100), 90)
        else:
            self.resource_settings['memory_limit'] = min(self.resource_settings.get('memory_limit', 100) + 5, 100)
        
        self.save_settings()
        self.log_optimization(data)

    def log_optimization(self, data):
        logger.info(str(f"Optimized resources with data: {data}\n").rstrip("\n"))

resource_optimizer = ResourceOptimizer()

def handle_system_health_event(data):
    resource_optimizer.optimize_resources(data)
    
    # Emit a resource optimization event
    event_bus.emit('RESOURCE_OPTIMIZATION', resource_optimizer.resource_settings)


def start_module(event_bus):
    event_bus.subscribe('SYSTEM_HEALTH_CHECK', handle_system_health_event)

    # Log module startup
    logger.info(str("ResourceOptimizer module started.\n").rstrip("\n"))
