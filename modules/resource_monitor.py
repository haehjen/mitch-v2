import os
import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/resource_monitor.log'

class ResourceMonitor:
    def __init__(self, cpu_threshold=80.0, memory_threshold=80.0, disk_threshold=90.0):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    def check_resources(self, event_data=None):
        """Check current system resource usage and log the status."""
        # Simulating resource usage check
        cpu_usage = self._get_cpu_usage()
        memory_usage = self._get_memory_usage()
        disk_usage = self._get_disk_usage()

        resource_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage
        }

        self._write_log(resource_data)
        self._emit_alerts(cpu_usage, memory_usage, disk_usage)

    def _get_cpu_usage(self):
        """Simulate retrieving CPU usage."""
        # This is a placeholder for actual CPU usage retrieval logic.
        return 50.0

    def _get_memory_usage(self):
        """Simulate retrieving Memory usage."""
        # This is a placeholder for actual Memory usage retrieval logic.
        return 70.0

    def _get_disk_usage(self):
        """Simulate retrieving Disk usage."""
        # This is a placeholder for actual Disk usage retrieval logic.
        return 85.0

    def _write_log(self, data):
        """Write the resource data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def _emit_alerts(self, cpu_usage, memory_usage, disk_usage):
        """Emit alerts if resource usage exceeds thresholds."""
        if cpu_usage > self.cpu_threshold:
            event_bus.emit('high_cpu_usage', {'cpu_usage': cpu_usage})
        if memory_usage > self.memory_threshold:
            event_bus.emit('high_memory_usage', {'memory_usage': memory_usage})
        if disk_usage > self.disk_threshold:
            event_bus.emit('high_disk_usage', {'disk_usage': disk_usage})


def start_module(event_bus):
    resource_monitor = ResourceMonitor()
    event_bus.subscribe('check_resources', resource_monitor.check_resources)
    
    print('Resource Monitor module started and listening for resource check events.')
    resource_monitor.check_resources()
