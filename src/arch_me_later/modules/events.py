from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

EventType = Enum("EventType", ["STATUS", "LOG", "METRIC"])

StatusType = Enum(
    "StatusType",
    ["SKIPPED", "PENDING", "STARTED", "IN_PROGRESS", "COMPLETED", "FAILED"],
)


@dataclass
class Metric:
    done: int
    total: int
    metric_name: str


@dataclass
class BaseEvent:
    time: datetime
    module: str
    step: str
    event_type: EventType


@dataclass
class StatusEvent(BaseEvent):
    status: StatusType

    @classmethod
    def from_dict(cls, data: dict) -> StatusEvent:
        return cls(
            time=datetime.fromisoformat(data["time"]),
            module=data["module"],
            step=data["step"],
            event_type=EventType.STATUS,
            status=StatusType[data["status"]],
        )


@dataclass
class LogEvent(BaseEvent):
    level: str
    message: str

    @classmethod
    def from_dict(cls, data: dict) -> LogEvent:
        return cls(
            time=datetime.fromisoformat(data["time"]),
            module=data["module"],
            step=data["step"],
            event_type=EventType.LOG,
            level=data["level"],
            message=data["message"],
        )


class MetricEvent(BaseEvent):
    metric: Metric

    @classmethod
    def from_dict(cls, data: dict) -> MetricEvent:
        return cls(
            time=datetime.fromisoformat(data["time"]),
            module=data["module"],
            step=data["step"],
            event_type=EventType.METRIC,
            metric=Metric(
                done=data["metric"]["done"],
                total=data["metric"]["total"],
                metric_name=data["metric"]["metric_name"],
            ),
        )


def parse_event(json_str: str) -> BaseEvent:
    data = json.loads(json_str)
    event_type = EventType[data["event_type"]]
    match event_type:
        case EventType.STATUS:
            return StatusEvent.from_dict(data)
        case EventType.LOG:
            return LogEvent.from_dict(data)
        case EventType.METRIC:
            return MetricEvent.from_dict(data)
        case _:
            raise ValueError(f"Unknown event type: {data['event_type']}")
