import os
import psutil
import logging
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SystemHealthMonitor:
    def __init__(self):
        self.cpu_threshold = 80  # CPU usage percentage
        self.memory_threshold = 80  # Memory usage percentage

    def check_system_health(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        if cpu_usage > self.cpu_threshold:
            self.emit_alert('CPU', cpu_usage)
        if memory_usage > self.memory_threshold:
            self.emit_alert('Memory', memory_usage)

    def emit_alert(self, resource_type, usage):
        alert_message = f"High {resource_type} usage detected: {usage}%"
        logging.warning(alert_message)
        event_bus.emit('system_health_alert', {'resource': resource_type, 'usage': usage})

    def handle_health_check_event(self, event_data):
        self.check_system_health()


def start_module(event_bus):
    monitor = SystemHealthMonitor()
    event_bus.subscribe('check_system_health', monitor.handle_health_check_event)
    logging.info("System Health Monitor module started and listening for health check events.")
