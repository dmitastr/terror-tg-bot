import json
from pypika import Query, Table, MySQLQuery

comment = """
sdfsdlkfjsdlf
sdfsdlfjs
sefsdf
🙏
"""
data = {
    "c": ["11", "12"],
    "comment": comment
}

row = {
    "user_id": 40322523,
    "username": "dmastr",
    "week_number": 1,
    "employee_type": "gamemaster",
    "data": json.dumps(data, ensure_ascii=False)
}


t = Table("shifts")
q = MySQLQuery.into(t).columns(*list(row)).insert(*list(row.values()))
query = str(q).replace("INSERT", "UPSERT")


print(query)
