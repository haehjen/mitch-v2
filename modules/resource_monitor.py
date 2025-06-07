import os
import json
import datetime
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("resource_monitor")

class ResourceMonitor:
    def __init__(self, cpu_threshold=80.0, memory_threshold=80.0, disk_threshold=90.0):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold

    def check_resources(self, event_data=None):
        """Check current system resource usage and log the status."""
        cpu_usage = self._get_cpu_usage()
        memory_usage = self._get_memory_usage()
        disk_usage = self._get_disk_usage()

        resource_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage
        }

        logger.info(f"Resource usage: CPU={cpu_usage}%, Memory={memory_usage}%, Disk={disk_usage}%")
        self._emit_alerts(cpu_usage, memory_usage, disk_usage)

    def _get_cpu_usage(self):
        return 50.0  # Placeholder for actual CPU usage

    def _get_memory_usage(self):
        return 70.0  # Placeholder for actual memory usage

    def _get_disk_usage(self):
        return 85.0  # Placeholder for actual disk usage

    def _emit_alerts(self, cpu_usage, memory_usage, disk_usage):
        """Emit alerts if resource usage exceeds thresholds."""
        if cpu_usage > self.cpu_threshold:
            logger.warning(f"High CPU usage detected: {cpu_usage}%")
            event_bus.emit('high_cpu_usage', {'cpu': cpu_usage, 'memory': memory_usage, 'disk': disk_usage})

        if memory_usage > self.memory_threshold:
            logger.warning(f"High Memory usage detected: {memory_usage}%")
            event_bus.emit('high_memory_usage', {'cpu': cpu_usage, 'memory': memory_usage, 'disk': disk_usage})

        if disk_usage > self.disk_threshold:
            logger.warning(f"High Disk usage detected: {disk_usage}%")
            event_bus.emit('high_disk_usage', {'cpu': cpu_usage, 'memory': memory_usage, 'disk': disk_usage})

def start_module(event_bus):
    resource_monitor = ResourceMonitor()
    event_bus.subscribe('check_resources', resource_monitor.check_resources)

    logger.info("Resource Monitor module started and listening for resource check events.")
    resource_monitor.check_resources()
