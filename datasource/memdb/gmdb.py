from datasource.models import GMDatabase, SlotsDB, TimePeriodDB, TimePeriodInfo, TimeSlot, EmployeeType


with open("data/gm_database.json", "r", encoding="utf-8") as f:
    data = f.read()

gm_database = GMDatabase.model_validate_json(data)

with open("data/slots_flat.json", "r", encoding="utf-8") as f:
    slots_data = f.read()

slots_database = SlotsDB.model_validate_json(slots_data)


time_period_database = TimePeriodDB(tp_names=[
    TimePeriodInfo(emp_type=EmployeeType.gamemaster,
                   time_slot=TimeSlot.MORNING, start="11³⁰", finish="18"),
    TimePeriodInfo(emp_type=EmployeeType.gamemaster,
                   time_slot=TimeSlot.EVENING, start="18", finish="00"),
    TimePeriodInfo(emp_type=EmployeeType.gamemaster,
                   time_slot=TimeSlot.NIGHT, start="00", finish="06"),

    TimePeriodInfo(emp_type=EmployeeType.admin,
                   time_slot=TimeSlot.MORNING, start="утро"),
    TimePeriodInfo(emp_type=EmployeeType.admin,
                   time_slot=TimeSlot.EVENING, start="вечер", finish="вечер"),
    TimePeriodInfo(emp_type=EmployeeType.admin,
                   time_slot=TimeSlot.DAY, start="15-21", finish="15-21"),
    TimePeriodInfo(emp_type=EmployeeType.admin,
                   time_slot=TimeSlot.NIGHT, start="ночь"),
])
