import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Callable

import arrow
from pydantic import BaseModel
import requests
from common.config import DEFAULT_SLOTS, time_format
from datasource import (
    gm_database,
    slots_database,
    time_period_database,
    EmployeeType,
    Slot,
    TimeSlot,
    TimePeriodDB
)
from datasource.sqlite.sqlite import SQLiteDataBase


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Availability(BaseModel):
    slots: List[str]
    availability_table: dict[str, dict[str, dict[str, str]]]


class ShiftsFilled(BaseModel):
    dates: List[str]
    shifts_table: dict[str, dict[str, str]]


class Schedule(BaseModel):
    availability: Availability
    shifts_filled: ShiftsFilled
    warnings: Optional[List[dict[str, str]]]


class Service:
    def __init__(self, db: SQLiteDataBase, api_key: str = ""):
        self.api_key = api_key
        self.db = db
        self.shift_table = 'shifts_available_new'
        self.schedule_create_url = 'https://functions.yandexcloud.net/d4eg0vivihaseh8igag4'

    def save_shifts(self, shift: Dict[str, Any]) -> None:
        user_id = shift.get('user_id')
        gms = gm_database.get_by_id_all(user_id)
        username = shift.get('username')
        if user_id and username:
            for gm in gms:
                self.db.insert_shifts(
                    user_id=int(gm.tg_id),
                    username=gm.username,
                    week_number=self.get_current_week_number(),
                    employee_type=gm.employee_type,
                    data=json.dumps(shift.get(
                        'selected_options', {}), ensure_ascii=False),
                    created_at=arrow.now().format(time_format),
                    table_name=self.shift_table
                )

    def get_current_week_number(self) -> int:
        return arrow.get().isocalendar()[1]

    def get_shifts(self, week_number: int | None, emp_type: EmployeeType) -> List[dict[str, Any]]:
        current_week = week_number or self.get_current_week_number()
        shifts = self.db.get_shifts(table_name=self.shift_table, field_filter={'week_number': [
                                    current_week], 'employee_type': [str(emp_type)]}, min_dttm=arrow.now().shift(days=-30).format(time_format))

        for shift in shifts:
            if shift.get("data"):
                shift['data'] = json.loads(shift['data'])

        shifts = self.fill_absent_shifts(shifts=shifts, emp_type=emp_type)

        return shifts

    # заполнить пустые смены Беса и Ромы
    def fill_absent_shifts(self, shifts: List[dict[str, Any]], emp_type: EmployeeType) -> List[dict[str, Any]]:
        slots_all = slots_database.get_default_shifts(emp_type=emp_type)
        gm_usernames_active = set(
            gm.username for gm in gm_database.get_by_type(emp_type).get_active().as_list())

        usernames = [shift['username'] for shift in shifts]
        usernames_absent = gm_usernames_active.difference(usernames)
        for username in usernames_absent:
            shifts.append({'username': username, 'week_number': self.get_current_week_number(),
                           'data': {'wants': DEFAULT_SLOTS.get(username, slots_all), 'cans': [], 'comment': 'autogenerate'}})

        return shifts

    def available_to_table(self, av_shifts: List[dict[str, Any]], schedule: dict[str, List[int]], emp_type: EmployeeType) -> Availability:
        gm_db = gm_database.get_by_type(emp_type=emp_type)
        slots = slots_database.get_slots(emp_type=emp_type)

        slots.sort(key=lambda x: x.id)

        white = "#ffffff"
        can_color = "#b7e1cd"
        want_color = "#57bb8a"
        blank_shift = {
            slot.get_name(): {"bgcolor": white, "value": ""}
            for slot in slots
        }

        table: dict[str, dict[str, dict[str, str]]] = {}
        for shifts in av_shifts:
            gm_username: str = shifts.get('username')
            gms_final_shifts: List[int] = schedule[gm_username]

            data = shifts.get('data', {})
            cans: List[str] = data.get('cans', [])
            wants: List[str] = data.get('wants', [])

            slots_data: dict[str, dict[str, str]] = {}
            for slot in slots:
                color = white
                if str(slot.id) in cans:
                    color = can_color
                elif str(slot.id) in wants:
                    color = want_color

                value = "1" if slot.id in gms_final_shifts else ""
                slots_data[slot.get_name()] = {
                    "bgcolor": color, "value": value}

            gm_name = gm_username
            gm = gm_db.get_by_username(gm_username)
            if gm:
                gm_name = gm.name
            table[gm_name] = slots_data

        for gm_name in self.get_gm_human_names(emp_type=emp_type):
            if gm_name not in table:
                table[gm_name] = blank_shift

        availability = Availability(
            slots=[slot.get_name() for slot in slots], availability_table=table)
        return availability

    def shifts_to_table(self, shifts: dict[str, List[int]], emp_type: EmployeeType) -> ShiftsFilled:
        # collapse slots and convert list of slots to list of time slot name for each person
        gm_db = gm_database.get_by_type(emp_type=emp_type)

        days_names = self.get_next_week_dates()
        blank_shift = {
            day_name: ''
            for day_name in days_names.values()
        }
        days: List[str] = [day[1] for day in sorted(
            list(days_names.items()), key=self.tuple_sort_func(0))]

        shifts_obj: dict[str, dict[str, str]] = {}
        for gm_username, gm_shifts in shifts.items():
            # logger.info(
            #     f"collapsing shifts for {gm_username}, shifts: {gm_shifts}")
            collapsed = self.collapse_shifts(
                shifts=gm_shifts, emp_type=emp_type)
            collapsed_with_names: dict[str, str] = {
                days_names[day]: shift_name
                for day, shift_name in collapsed.items()
            }

            for day_name in days_names.values():
                if day_name not in collapsed_with_names:
                    collapsed_with_names[day_name] = ""

            gm_name = gm_username
            gm = gm_db.get_by_username(gm_username)
            if gm:
                gm_name = gm.name
            shifts_obj[gm_name] = collapsed_with_names

        for gm_name in self.get_gm_human_names(emp_type=emp_type):
            if gm_name not in shifts_obj:
                shifts_obj[gm_name] = blank_shift

        shifts_filled = ShiftsFilled(dates=days, shifts_table=shifts_obj)
        logger.info(f"Created shifts table: {shifts_obj}")
        return shifts_filled

    def get_gm_human_names(self, emp_type: EmployeeType) -> List[str]:
        gm_names: List[str] = gm_database.get_by_type(
            emp_type).get_active().as_list()
        gm_names = sorted(
            gm_names, key=lambda x: x.id)

        return [gm.name for gm in gm_names]

    def collapse_shifts(self, shifts: List[int], emp_type: EmployeeType) -> dict[int, str]:
        # collapse  slots within one day and return  start-finish info of all slots for certain day
        shifts = sorted(shifts)
        shifts_info: List[Slot] = [Slot(id=s, capacity=1) for s in shifts]
        collapsed_shifts: dict[int, str] = {}

        if len(shifts_info) == 1:
            collapsed_shifts[shifts_info[0].day] = time_period_database.get_tp_name(
                emp_type=emp_type,
                start=shifts_info[0].time_period)

            return collapsed_shifts

        elif len(shifts_info) == 0:
            return collapsed_shifts

        shift_start = shifts_info[0]
        for idx in range(1, len(shifts_info)):
            curr_shift = shifts_info[idx]
            if curr_shift.day != shift_start.day:
                # logger.info(
                #     f"Collapsing day:{shift_start.day}, start: {shift_start.time_period}, finish:{shifts_info[idx-1].time_period}")
                collapsed_shifts[shift_start.day] = time_period_database.get_tp_name(
                    emp_type=emp_type,
                    start=shift_start.time_period,
                    finish=shifts_info[idx-1].time_period)
                shift_start = curr_shift

        if not collapsed_shifts.get(curr_shift.day):
            collapsed_shifts[curr_shift.day] = time_period_database.get_tp_name(
                emp_type=emp_type,
                finish=curr_shift.time_period,
                start=shift_start.time_period)

        return collapsed_shifts

    def tuple_sort_func(self, idx: int) -> Callable:
        def sort_func(value: Tuple[Any]) -> Any:
            return value[idx]
        return sort_func

    def schedule_create(self, week_number: int | None, emp_type: EmployeeType) -> Schedule:
        with requests.Session() as s:
            s.headers.update({'Authorization': f'Bearer {self.api_key}',
                             'Content-Type': 'application/json', 'Accept': 'application/json'})
            shifts = self.get_shifts(week_number, emp_type=emp_type)
            if not shifts:
                logger.error('no shifts for next week')
                return

            slots = slots_database.get_slots(emp_type)
            payload = {'shifts': shifts,
                       'slots': [slot.model_dump() for slot in slots]}
            response: requests.Response = s.post(
                self.schedule_create_url, data=json.dumps(payload))

            if response.status_code != 200:
                logger.error(f"error while creating schedule: {response.text}")
                return

            data: dict = response.json()
            schedule: dict[str, List[int]] = data.get('shifts', {})
            if not schedule:
                logger.error("No shifts were assigned")
                return

            warnings: List[dict[str, str]] = data.get('warnings', [])

            shifts_filled = self.shifts_to_table(schedule, emp_type)
            av_shifts = self.available_to_table(
                av_shifts=shifts, schedule=schedule, emp_type=emp_type)
            schedule_obj = Schedule(availability=av_shifts,
                                    shifts_filled=shifts_filled, warnings=warnings)

            return schedule_obj  # kotya sex

    def get_next_week_dates(self) -> dict[int, str]:
        # Словарь сокращений дней недели на русском
        weekdays = {
            0: "пн",
            1: "вт",
            2: "ср",
            3: "чт",
            4: "пт",
            5: "сб",
            6: "вс",
        }

        today: arrow.Arrow = arrow.now()
        # Найдём следующий понедельник
        days_until_next_monday: int = (7 - today.weekday()) % 7
        next_monday: arrow.Arrow = today.shift(
            days=+days_until_next_monday).floor('day')

        result = {}
        for i in range(7):
            day = next_monday.shift(days=+i)
            weekday_name = weekdays[i]
            formatted_date = day.format("DD.MM")
            result[i + 1] = f"{weekday_name} {formatted_date}"

        return result
