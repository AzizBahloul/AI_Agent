#!/usr/bin/env python3
"""
Real-time performance monitor for MCP AI Agent
"""

import time
import psutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import threading


class PerformanceMonitor:
    """Real-time performance monitoring"""

    def __init__(self, update_interval: float = 5.0):
        self.update_interval = update_interval
        self.monitoring = False
        self.metrics = []
        self.start_time = None

    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.start_time = datetime.now()

        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

        print("📊 Performance monitoring started")

    def stop_monitoring(self):
        """Stop monitoring and save results"""
        self.monitoring = False
        self._save_metrics()
        print("📊 Performance monitoring stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics.append(metrics)

                # Keep only last 100 measurements
                if len(self.metrics) > 100:
                    self.metrics.pop(0)

                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(self.update_interval)

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect system metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_gb": memory.used / (1024**3),
            "disk_percent": (disk.used / disk.total) * 100,
            "process_count": len(psutil.pids()),
        }

    def _save_metrics(self):
        """Save metrics to file"""
        if not self.metrics:
            return

        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)

        summary = {
            "session_start": self.start_time.isoformat() if self.start_time else None,
            "session_duration_seconds": (
                datetime.now() - self.start_time
            ).total_seconds()
            if self.start_time
            else 0,
            "metrics_count": len(self.metrics),
            "average_cpu": sum(m["cpu_percent"] for m in self.metrics)
            / len(self.metrics),
            "average_memory": sum(m["memory_percent"] for m in self.metrics)
            / len(self.metrics),
            "peak_cpu": max(m["cpu_percent"] for m in self.metrics),
            "peak_memory": max(m["memory_percent"] for m in self.metrics),
            "detailed_metrics": self.metrics,
        }

        with open(data_dir / "performance_report.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"📊 Performance report saved: {len(self.metrics)} data points")

    def get_current_status(self) -> Dict[str, Any]:
        """Get current performance status"""
        if not self.metrics:
            return {"status": "No data available"}

        latest = self.metrics[-1]
        return {
            "cpu_percent": latest["cpu_percent"],
            "memory_percent": latest["memory_percent"],
            "status": "healthy"
            if latest["cpu_percent"] < 80 and latest["memory_percent"] < 80
            else "high_usage",
        }


# Global monitor instance
performance_monitor = PerformanceMonitor()

if __name__ == "__main__":
    monitor = PerformanceMonitor(1.0)  # Update every second
    monitor.start_monitoring()

    try:
        while True:
            status = monitor.get_current_status()
            print(
                f"CPU: {status.get('cpu_percent', 0):.1f}% | Memory: {status.get('memory_percent', 0):.1f}%"
            )
            time.sleep(5)
    except KeyboardInterrupt:
        monitor.stop_monitoring()
