import os
import json
import psutil
from datetime import datetime
from core.event_bus import event_bus

LOG_FILE = '/home/triad/mitch/logs/adaptive_energy_manager.log'

class AdaptiveEnergyManager:
    def __init__(self):
        self.cpu_threshold = 70  # CPU usage percentage to trigger energy-saving mode
        self.memory_threshold = 70  # Memory usage percentage to trigger energy-saving mode
        self.log_action('Adaptive Energy Manager initialized.')

    def log_action(self, message):
        with open(LOG_FILE, 'a') as log_file:
            log_file.write(f'{datetime.now().isoformat()} - {message}\n')

    def monitor_resources(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent

        self.log_action(f'CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%')

        if cpu_usage > self.cpu_threshold or memory_usage > self.memory_threshold:
            self.activate_energy_saving_mode()
        else:
            self.deactivate_energy_saving_mode()

    def activate_energy_saving_mode(self):
        self.log_action('Activating energy-saving mode.')
        # Emit event to notify other modules to reduce activity
        event_bus.emit('ENERGY_SAVING_MODE', {'status': 'activate'})

    def deactivate_energy_saving_mode(self):
        self.log_action('Deactivating energy-saving mode.')
        # Emit event to notify other modules to resume normal activity
        event_bus.emit('ENERGY_SAVING_MODE', {'status': 'deactivate'})

    def start_monitoring(self):
        self.log_action('Starting resource monitoring.')
        # Continuously monitor resources in a loop
        while True:
            self.monitor_resources()


def start_module(event_bus):
    energy_manager = AdaptiveEnergyManager()
    event_bus.subscribe('RESOURCE_MONITOR', energy_manager.monitor_resources)
    energy_manager.start_monitoring()
