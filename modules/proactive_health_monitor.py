import os
import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/proactive_health_monitor.log'

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
        self._write_log(usage_data)

    def _write_log(self, data):
        """Write the resource usage data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def analyze_and_optimize(self):
        """Analyze the logged resource usage and take action to optimize system performance."""
        # Simplified analysis logic, can be expanded with more complex algorithms
        if len(self.resource_usage) > 5:
            recent_usages = self.resource_usage[-5:]
            avg_cpu = sum(entry['cpu'] for entry in recent_usages) / 5
            avg_memory = sum(entry['memory'] for entry in recent_usages) / 5
            if avg_cpu > 50 or avg_memory > 70:
                # Emit an event to optimize system
                event_bus.emit('OPTIMIZE_SYSTEM', {'cpu': avg_cpu, 'memory': avg_memory})

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
    
    print('Proactive Health Monitor module started and listening for high resource usage events.')
