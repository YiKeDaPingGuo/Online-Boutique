from __future__ import annotations

from abc import ABC, abstractmethod

from aiops_agent.config import AppConfig
from aiops_agent.types import MetricPoint


class DataSource(ABC):
    def __init__(self, config: AppConfig):
        self.config = config

    @abstractmethod
    def collect(self) -> list[MetricPoint]:
        """Return normalized metric points."""

