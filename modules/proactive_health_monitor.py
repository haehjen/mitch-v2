import json
import datetime
from core.event_bus import event_bus
from core.peterjones import get_logger

logger = get_logger("health_monitor")

class ProactiveHealthMonitor:
    def __init__(self):
        self.resource_usage = []

    def log_resource_usage(self, cpu, memory, disk):
        """Log the resource usage data."""
        timestamp = datetime.datetime.now().isoformat()
        usage_data = {
            'timestamp': timestamp,
            'cpu': cpu,
            'memory': memory,
            'disk': disk
        }
        self.resource_usage.append(usage_data)
        logger.info(f"Resource usage logged: CPU={cpu}%, Memory={memory}%, Disk={disk}%")

    def analyze_and_optimize(self):
        """Analyze the logged resource usage and take action to optimize system performance."""
        if len(self.resource_usage) > 5:
            recent_usages = self.resource_usage[-5:]
            avg_cpu = sum(entry['cpu'] for entry in recent_usages) / 5
            avg_memory = sum(entry['memory'] for entry in recent_usages) / 5

            logger.debug(f"Avg CPU: {avg_cpu}%, Avg Memory: {avg_memory}%")

            if avg_cpu > 50 or avg_memory > 70:
                logger.warning(f"Triggering optimization: CPU={avg_cpu:.2f}%, Memory={avg_memory:.2f}%")
                event_bus.emit('OPTIMIZE_SYSTEM', {'cpu': avg_cpu, 'memory': avg_memory})
            else:
                logger.info("System performance within acceptable range.")
        else:
            logger.debug("Not enough data points to analyze resource usage.")

    def handle_high_cpu_usage(self, event_data):
        """Handle high CPU usage events."""
        self.log_resource_usage(event_data.get('cpu'), event_data.get('memory'), event_data.get('disk'))
        self.analyze_and_optimize()

    def handle_high_memory_usage(self, event_data):
        """Handle high memory usage events."""
        self.log_resource_usage(event_data.get('cpu'), event_data.get('memory'), event_data.get('disk'))
        self.analyze_and_optimize()

def start_module(event_bus):
    monitor = ProactiveHealthMonitor()
    event_bus.subscribe('high_cpu_usage', monitor.handle_high_cpu_usage)
    event_bus.subscribe('high_memory_usage', monitor.handle_high_memory_usage)

    logger.info("Proactive Health Monitor module started and listening for high resource usage events.")
