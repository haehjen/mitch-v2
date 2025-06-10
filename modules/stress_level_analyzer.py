import os
import json
import datetime
from core.event_bus import event_bus

LOG_FILE_PATH = '/home/triad/mitch/logs/stress_level_analyzer.log'

class StressLevelAnalyzer:
    def __init__(self):
        self.cpu_threshold = 80.0  # Example threshold values
        self.memory_threshold = 80.0
        self.disk_threshold = 90.0

    def analyze_resources(self, event_data):
        """Analyze resource usage and log stress level."""
        cpu_usage = event_data.get('cpu_usage', 0)
        memory_usage = event_data.get('memory_usage', 0)
        disk_usage = event_data.get('disk_usage', 0)

        stress_level = 'Normal'
        if cpu_usage > self.cpu_threshold or memory_usage > self.memory_threshold or disk_usage > self.disk_threshold:
            stress_level = 'High'

        log_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'stress_level': stress_level
        }
        self._write_log(log_data)
        
        if stress_level == 'High':
            event_bus.emit('high_stress_detected', log_data)

    def _write_log(self, data):
        """Write the stress level data to the log file."""
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')


def start_module(event_bus):
    stress_analyzer = StressLevelAnalyzer()
    event_bus.subscribe('resource_usage', stress_analyzer.analyze_resources)
    print('Stress Level Analyzer module started and listening for resource usage events.')
