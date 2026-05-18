# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Dict, Optional

class TaskStats:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskStats, cls).__new__(cls)
            cls._instance.start_time: Optional[datetime] = None
            cls._instance.end_time: Optional[datetime] = None
            cls._instance.total_count: int = 0
            cls._instance.platform: str = ""
            cls._instance.is_running: bool = False
        return cls._instance

    def reset(self, platform: str):
        self.start_time = datetime.now()
        self.end_time = None
        self.total_count = 0
        self.platform = platform
        self.is_running = True

    def finish(self, count: int):
        self.end_time = datetime.now()
        self.total_count = count
        self.is_running = False

    def get_summary(self) -> Dict:
        return {
            "platform": self.platform,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S") if self.start_time else None,
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "duration": str(self.end_time - self.start_time).split('.')[0] if self.start_time and self.end_time else None,
            "total_count": self.total_count,
            "is_running": self.is_running
        }

task_stats = TaskStats()
