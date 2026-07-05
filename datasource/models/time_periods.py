
from pydantic import BaseModel, model_validator
from typing import List, Optional, Any
from .gm import EmployeeType
from enum import IntEnum


class TimeSlot(IntEnum):
    EVENING = 3
    MORNING = 1
    NIGHT = 5
    DAY = 4


class TimePeriodInfo(BaseModel):
    emp_type: EmployeeType
    time_slot: TimeSlot
    start: str
    finish: Optional[str] = None

    @model_validator(mode='before')
    def fill_finish_time(cls, data: Any) -> Any:
        if "finish" not in data:
            data["finish"] = data["start"]
        return data

    def get_name(self, delim: str = " - ") -> str:
        if self.finish and self.emp_type == EmployeeType.gamemaster:
            return f"{self.start}{delim}{self.finish}"
        return self.start


class TimePeriodDB(BaseModel):
    tp_names: List[TimePeriodInfo]

    def get_tp_name(self, emp_type: EmployeeType, start: TimeSlot, finish: Optional[TimeSlot] = None) -> str:
        match emp_type:
            case EmployeeType.admin:
                delim = "/"
            case EmployeeType.gamemaster:
                delim = " - "
            case _:
                delim = " - "

        start_tp = self.get_tp(emp_type, start)

        if finish:
            finish_tp = self.get_tp(emp_type, finish)
            if finish_tp.time_slot != start_tp.time_slot:
                if finish_tp.finish:
                    return f"{start_tp.start}{delim}{finish_tp.finish}"

                if start_tp.start == finish_tp.start:
                    return start_tp.start

                return f"{start_tp.start}{delim}{finish_tp.start}"

        return start_tp.get_name(delim=delim)

    def get_tp(self, emp_type: EmployeeType, time_slot: TimeSlot) -> TimePeriodInfo:
        for tp in self.tp_names:
            if tp.emp_type == emp_type and tp.time_slot == time_slot:
                return tp
