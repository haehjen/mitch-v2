import time
from core.event_bus import event_bus, INNERMONO_PATH
import os
import json

LOG_FILE_PATH = INNERMONO_PATH
CHECK_INTERVAL = 300  # Check every 5 minutes

class SystemHealthChecker:
    def __init__(self):
        self.module_status = {}

    def log_health_status(self, status):
        """Log the health status to a file."""
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
        log_entry = {
            'timestamp': timestamp,
            'status': status
        }
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(log_entry) + '\n')

    def check_system_resources(self):
        """Check the current status of system resources."""
        # For simplicity, let's simulate resource check
        cpu_usage = 20.0  # Simulated value
        memory_usage = 50.0  # Simulated value
        disk_usage = 70.0  # Simulated value
        return {
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage
        }

    def check_module_status(self):
        """Check the status of important modules."""
        # Simulate module status check
        self.module_status['resource_monitor'] = 'active'
        self.module_status['adaptive_response'] = 'active'
        self.module_status['anomaly_detector'] = 'inactive'  # Simulated issue
        return self.module_status

    def evaluate_system_health(self):
        """Evaluate the overall health based on resource and module status."""
        resource_status = self.check_system_resources()
        active_modules = self.check_module_status()

        # Determine health based on thresholds
        if resource_status['cpu_usage'] > 80.0 or resource_status['memory_usage'] > 80.0 or resource_status['disk_usage'] > 85.0:
            health_status = 'Warning: High resource usage detected.'
        elif 'inactive' in active_modules.values():
            health_status = 'Warning: Some modules are inactive.'
        else:
            health_status = 'System healthy.'

        self.log_health_status(health_status)
        return health_status

    def start_monitoring(self):
        """Start the continuous monitoring loop."""
        while True:
            self.evaluate_system_health()
            time.sleep(CHECK_INTERVAL)


def start_module(event_bus):
    health_checker = SystemHealthChecker()
    event_bus.subscribe('CHECK_SYSTEM_HEALTH', lambda data: health_checker.evaluate_system_health())
    
    health_checker.start_monitoring()
    print('System Health Checker module started and monitoring system health.')
