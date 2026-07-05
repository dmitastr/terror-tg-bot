from typing import Dict, List

from pydantic import BaseModel, model_validator

from .gm import EmployeeType

weekdays = {
    0: "пн",
    1: "вт",
    2: "ср",
    3: "чт",
    4: "пт",
    5: "сб",
    6: "вс",
}


period_names = {
    1: "утро",
    3: "вечер",
    4: "15-21",
    5: "ночь",
}


class Slot(BaseModel):
    id: int
    day: int
    time_period: int
    capacity: int
    employee_type: EmployeeType | None = None

    @model_validator(mode="before")
    @classmethod
    def compute_day_and_time(cls, data: dict):
        slot_id = data.get("id")

        if slot_id is not None:
            data["day"] = slot_id // 10
            data["time_period"] = slot_id % 10

        return data

    def get_name(self) -> str:
        return f"{weekdays[self.day-1]} {period_names[self.time_period]}"


class SlotsDB(BaseModel):
    slots: List[Slot]

    def get_default_shifts(self, emp_type: EmployeeType) -> List[str]:
        if emp_type == EmployeeType.admin:
            return []
        return self.as_list(emp_type=emp_type)

    def get_slots(self, emp_type: EmployeeType) -> List[Slot]:
        return [slot for slot in self.slots if slot.employee_type == emp_type]

    def as_list(self, emp_type: EmployeeType) -> List[str]:
        slots: List[str] = [
            str(slot.id)
            for slot in self.get_slots(emp_type=emp_type)
        ]
        return slots


if __name__ == "__main__":
    slots_db = SlotsDB.model_validate_json(
        '{"slots_by_type": {"gamemaster": { "slots": { "11": { "id": 11,"capacity": 4}}}}}')

    tp = EmployeeType.gamemaster

    print(slots_db.get_slots(tp))
