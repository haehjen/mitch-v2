import os
import json
import time
import psutil
from core.event_bus import event_bus, INNERMONO_PATH

LOG_FILE_PATH = INNERMONO_PATH
ALERT_THRESHOLD = 80.0  # Percentage of bandwidth usage that triggers an alert
CHECK_INTERVAL = 60  # Time in seconds between checks

class NetworkStatusMonitor:
    def __init__(self):
        self.previous_bytes_sent = psutil.net_io_counters().bytes_sent
        self.previous_bytes_recv = psutil.net_io_counters().bytes_recv

    def log_network_status(self, data):
        with open(LOG_FILE_PATH, 'a') as log_file:
            log_file.write(json.dumps(data) + '\n')

    def check_network_status(self):
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent
        bytes_recv = net_io.bytes_recv

        bytes_sent_diff = bytes_sent - self.previous_bytes_sent
        bytes_recv_diff = bytes_recv - self.previous_bytes_recv

        self.previous_bytes_sent = bytes_sent
        self.previous_bytes_recv = bytes_recv

        # Calculate usage as percentage of total available bandwidth
        # Assuming a placeholder bandwidth value for demonstration
        total_bandwidth = 1000000  # in bytes per second, adjust as needed

        usage_sent = (bytes_sent_diff / total_bandwidth) * 100
        usage_recv = (bytes_recv_diff / total_bandwidth) * 100

        # Log network status
        network_data = {
            'timestamp': time.time(),
            'bytes_sent_diff': bytes_sent_diff,
            'bytes_recv_diff': bytes_recv_diff,
            'usage_sent_percentage': usage_sent,
            'usage_recv_percentage': usage_recv
        }
        self.log_network_status(network_data)

        # Check for high usage
        if usage_sent > ALERT_THRESHOLD:
            event_bus.emit('high_network_usage', {'type': 'sent', 'usage': usage_sent})
        if usage_recv > ALERT_THRESHOLD:
            event_bus.emit('high_network_usage', {'type': 'recv', 'usage': usage_recv})

    def start_monitoring(self):
        while True:
            self.check_network_status()
            time.sleep(CHECK_INTERVAL)


def start_module(event_bus):
    monitor = NetworkStatusMonitor()
    event_bus.subscribe('start_network_monitor', monitor.start_monitoring)
    event_bus.emit('network_monitor_started', {'status': 'Network Status Monitor started'})
    print('Network Status Monitor module started and monitoring network status.')
