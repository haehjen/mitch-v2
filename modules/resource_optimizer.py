import os
import psutil
import time
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

logger = get_logger("resource_optimizer")

class ResourceOptimizer:
    def __init__(self):
        self.cpu_threshold = 80  # in percentage
        self.memory_threshold = 80
        self.disk_threshold = 80
        self.running = True

    def check_resources(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        logger.info(f"CPU: {cpu_usage}%, Memory: {memory_usage}%, Disk: {disk_usage}%")

        if cpu_usage > self.cpu_threshold:
            logger.warning(f"CPU usage threshold exceeded: {cpu_usage}%")
            event_bus.emit('high_cpu_usage', {'cpu_usage': cpu_usage})
        if memory_usage > self.memory_threshold:
            logger.warning(f"Memory usage threshold exceeded: {memory_usage}%")
            event_bus.emit('high_memory_usage', {'memory_usage': memory_usage})
        if disk_usage > self.disk_threshold:
            logger.warning(f"Disk usage threshold exceeded: {disk_usage}%")
            event_bus.emit('high_disk_usage', {'disk_usage': disk_usage})

    def handle_high_cpu_usage(self, data):
        logger.info(f"Handling high CPU usage: {data}")
        # CPU optimization logic would go here

    def handle_high_memory_usage(self, data):
        logger.info(f"Handling high Memory usage: {data}")
        # Memory optimization logic would go here

    def handle_high_disk_usage(self, data):
        logger.info(f"Handling high Disk usage: {data}")
        # Disk optimization logic would go here

    def start(self):
        event_bus.subscribe('high_cpu_usage', self.handle_high_cpu_usage)
        event_bus.subscribe('high_memory_usage', self.handle_high_memory_usage)
        event_bus.subscribe('high_disk_usage', self.handle_high_disk_usage)
        self.running = True

        logger.info("Resource Optimizer module started.")
        while self.running:
            self.check_resources()
            for _ in range(10):
                if not self.running:
                    break
                time.sleep(1)

    def shutdown(self, _=None):
        self.running = False
        logger.info("Resource Optimizer module shutting down.")

def start_module(event_bus):
    optimizer = ResourceOptimizer()
    event_bus.subscribe('SHUTDOWN', optimizer.shutdown)
    optimizer.start()
