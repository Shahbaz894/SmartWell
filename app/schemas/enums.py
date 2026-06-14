from enum import Enum

class TriggerType(str, Enum):
    physical = "physical"
    schedule = "schedule"
    app = "app"
    time = "time"