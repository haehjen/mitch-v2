import os
import psutil
import time
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/resource_optimizer.log'

class ResourceOptimizer:
    def __init__(self):
        self.cpu_threshold = 80  # in percentage
        self.memory_threshold = 80  # in percentage
        self.disk_threshold = 80  # in percentage

    def log(self, message):
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(message + '\n')

    def check_resources(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        self.log(f'CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%, Disk Usage: {disk_usage}%')

        # Emit events based on resource usage
        if cpu_usage > self.cpu_threshold:
            event_bus.emit('high_cpu_usage', {'cpu_usage': cpu_usage})
        if memory_usage > self.memory_threshold:
            event_bus.emit('high_memory_usage', {'memory_usage': memory_usage})
        if disk_usage > self.disk_threshold:
            event_bus.emit('high_disk_usage', {'disk_usage': disk_usage})

    def handle_high_cpu_usage(self, data):
        self.log(f'Handling high CPU usage: {data}')
        # Implement CPU optimization strategies here

    def handle_high_memory_usage(self, data):
        self.log(f'Handling high Memory usage: {data}')
        # Implement memory optimization strategies here

    def handle_high_disk_usage(self, data):
        self.log(f'Handling high Disk usage: {data}')
        # Implement disk optimization strategies here

    def start(self):
        event_bus.subscribe('high_cpu_usage', self.handle_high_cpu_usage)
        event_bus.subscribe('high_memory_usage', self.handle_high_memory_usage)
        event_bus.subscribe('high_disk_usage', self.handle_high_disk_usage)

        # Continuously check resources
        while True:
            self.check_resources()
            
            # Sleep for a predefined interval to avoid excessive resource usage
            time.sleep(10)


def start_module(event_bus):
    optimizer = ResourceOptimizer()
    optimizer.start()
