import json
from typing import Any, Dict, List


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


def get_slot_name(slot_id: int) -> str:
    day_name: str = weekdays.get(slot_id//10-1)
    period_name: str = period_names.get(slot_id % 10)
    return day_name + " " + period_name


def slots_flatten():
    with open("slots.json") as f:
        slots = json.load(f)

    slots: Dict[str, Dict[str, Dict]] = slots.get("slots_by_type", {})
    slots_flat: List[Dict] = []

    for tp, slots_for_week in slots.items():
        slots_data: Dict[str, Dict] = {}
        if slots_data := slots_for_week.get("slots"):
            for slot_id, slot in slots_data.items():
                slot["employee_type"] = tp
                slots_flat.append(slot)

    slots_flat.sort(key=lambda slot: slot["employee_type"] + str(slot["id"]))

    slots_export = {"slots": slots_flat}
    with open("slots_flat.json", "w") as f:
        json.dump(slots_export, f, indent=4)


def slots_check():
    with open("slots.json") as f:
        slots = json.load(f)

    slots: Dict[str, Dict[str, Dict]] = slots.get("slots_by_type", {})

    for tp, slots_for_week in slots.items():
        slots_data: Dict[str, Dict] = {}
        if slots_data := slots_for_week.get("slots"):
            slots_lst: List[List[Any]] = []
            for slot_id, slot in slots_data.items():
                if slot_id != str(slot.get("id")):
                    print(
                        f"Slot ids are not equal: {slot_id} != {slot.get("id")}")
                slots_lst.append([slot_id, get_slot_name(
                    slot.get("id")), slot.get("capacity", 0)])

            slots_lst.sort(key=lambda x: x[0])
            print(tp)
            print("\n".join(["{:10s} {:3d}".format(s[1], s[2])
                  for s in slots_lst]))
            print("----------")

        else:
            print(f"{tp} slots empty")


def main():
    slots_flatten()


if __name__ == "__main__":
    main()
