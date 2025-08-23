import os
import logging
import psutil
from core.event_bus import event_bus

# Set up logging
log_path = "/home/triad/mitch/logs/innermono.log"
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ResourceOptimizer:
    def __init__(self):
        self.thresholds = {
            'cpu': 80,  # CPU usage threshold
            'memory': 80  # Memory usage threshold
        }
        self.priority_rules = {
            'high': ['critical_process_1', 'critical_process_2'],
            'low': ['non_critical_process_1', 'non_critical_process_2']
        }

    def optimize_resources(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        logging.info(f"Current CPU usage: {cpu_usage}%, Memory usage: {memory_usage}%")

        if cpu_usage > self.thresholds['cpu'] or memory_usage > self.thresholds['memory']:
            logging.info("High resource usage detected, optimizing...")
            self.adjust_priorities()

    def adjust_priorities(self):
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['name'] in self.priority_rules['high']:
                    proc.nice(psutil.HIGH_PRIORITY_CLASS)
                    logging.info(f"Set high priority for process {proc.info['name']} (PID: {proc.info['pid']})")
                elif proc.info['name'] in self.priority_rules['low']:
                    proc.nice(psutil.IDLE_PRIORITY_CLASS)
                    logging.info(f"Set low priority for process {proc.info['name']} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logging.warning(f"Failed to adjust priority for process {proc.info['name']} (PID: {proc.info['pid']}): {e}")

    def handle_system_check_event(self, event_data):
        logging.info("Handling system check event...")
        self.optimize_resources()


def start_module(event_bus):
    optimizer = ResourceOptimizer()
    event_bus.subscribe('system_check', optimizer.handle_system_check_event)
    logging.info("Resource Optimizer module started and listening for system check events.")
