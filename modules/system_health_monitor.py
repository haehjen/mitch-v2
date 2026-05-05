import psutil
import time

from core.event_bus import event_bus
from core.peterjones import get_logger

HEALTH_MONITOR_INTERVAL = 60  # Check every 60 seconds
CPU_USAGE_THRESHOLD = 80  # Alert if CPU usage exceeds 80%
MEMORY_USAGE_THRESHOLD = 80  # Alert if Memory usage exceeds 80%
logger = get_logger("system_health_monitor")

class SystemHealthMonitor:
    def __init__(self):
        self.cpu_usage_threshold = CPU_USAGE_THRESHOLD
        self.memory_usage_threshold = MEMORY_USAGE_THRESHOLD

    def check_system_health(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent

        issues = []
        if cpu_usage > self.cpu_usage_threshold:
            issues.append(f"High CPU usage detected: {cpu_usage}%")
        if memory_usage > self.memory_usage_threshold:
            issues.append(f"High Memory usage detected: {memory_usage}%")

        if issues:
            self.emit_alerts(issues)
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "issues": issues,
        }

    def emit_alerts(self, issues):
        alert_message = "\n".join(issues)
        logger.warning(f"System Health Alert: {alert_message}")

        event_bus.emit("SYSTEM_HEALTH_ALERT", {"message": alert_message})

    def run(self):
        while True:
            self.check_system_health()
            time.sleep(HEALTH_MONITOR_INTERVAL)


def start_module(event_bus):
    monitor = SystemHealthMonitor()
    event_bus.subscribe("SYSTEM_HEALTH_CHECK", lambda data: monitor.check_system_health())

    def _handle_health_intent(_text):
        snapshot = monitor.check_system_health()
        issues = snapshot.get("issues", [])
        if issues:
            summary = "; ".join(issues)
        else:
            summary = (
                f"System health looks normal right now. "
                f"CPU is {snapshot['cpu_usage']:.1f}% and memory is {snapshot['memory_usage']:.1f}%."
            )
        event_bus.emit(
            "EMIT_CHAT_REQUEST",
            {
                "prompt": f"Give a concise system-health response: {summary}",
                "force_openai_minimal": True,
                "request_type": "system_health",
            },
        )
    
    from core.event_registry import IntentRegistry
    IntentRegistry.register_intent(
        "check_system_health",
        _handle_health_intent,
        keywords=[
            "system health",
            "check system health",
            "health check",
            "system diagnostics",
            "resource usage",
        ],
        objects=[],
        priority=2,
    )

    logger.info("SystemHealthMonitor module started.")

    from threading import Thread
    Thread(target=monitor.run, daemon=True).start()
