from typing import Any
import sqlite3
import logging
from pypika import Table, SQLLiteQuery, functions as fn
from pypika.queries import QueryBuilder

from datasource.models.gm import EmployeeType

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

INSERT_QUERY_TEMPLATE = 'UPSERT INTO {table_name} ({columns_clause}) VALUES ({values_clause})'
FILTER_QUERY_TEMPLATE = 'SELECT {columns} FROM {table_name} {where_clause} {order_by_clause} {limit_clause}'
DELETE_QUERY_TEMPLATE = "DELETE FROM {table_name} {where_clause}"
WHERE_CLAUSE_TEMPLATE = '{field} IN ({field_values_query})'


class SQLiteDataBase:
    def __init__(self, path: str) -> None:
        self.connection = sqlite3.connect(path)
        self.cur = self.connection.cursor()

    def insert_row(self, new_row: dict[str, Any], table_name: str) -> list[dict]:
        tbl: Table = Table(table_name)
        cols: list[str] = list(new_row.keys())
        vals: list[Any] = list(new_row.values())
        q = SQLLiteQuery.into(tbl).columns(*cols).insert(*vals)

        logger.info(q)

        return self.execute_query(q.get_sql())

    def insert_rows(self, new_rows: list[dict], table_name: str) -> None:
        for row in new_rows:
            self.insert_row(row, table_name=table_name)

    def update_rows(self, new_rows: list[dict], table_name: str) -> None:
        self.insert_rows(new_rows=new_rows, table_name=table_name)

    def delete(
        self,
        table_name: str,
        field_filter: dict[str, Any] = {},
    ) -> list[dict]:

        where_clause = ""
        if field_filter:
            where_clauses = [
                self.create_where_clause(field, values)
                for field, values in field_filter.items()
            ]
            where_clause = 'WHERE ' + ' AND '.join(where_clauses)

        query = DELETE_QUERY_TEMPLATE.format(
            table_name=table_name, where_clause=where_clause)
        return self.execute_query(query)

    def execute_query(self, query: str) -> list[tuple]:
        result_sets = self.cur.execute(query).fetchall()
        self.connection.commit()

        return result_sets

    def parse_row(self, row: tuple, columns: list[str]) -> dict[str, Any]:
        res_parsed = {}
        for value, col in zip(row, columns):
            res_parsed[col] = value
        return res_parsed

    def create_select_query(
        self,
        table_name: str,
        columns: list[str],
        field_filter: dict[str, list[Any]] = {},
        order_by: list[list[Any]] = [],
        limit: int = 0,
        min_dttm: str = None
    ) -> str:

        table = Table(table_name)
        q = SQLLiteQuery.from_(table).select(*columns)

        for field, values in field_filter.items():
            q = q.where(table[field].isin(values))

        for field, order in order_by:
            q = q.orderby(field, order)

        if min_dttm:
            q = q.where(table.created_at >= min_dttm)
        if limit:
            q = q.limit(limit)

        logger.info(q.get_sql())
        return q.get_sql()

    def create_where_clause(self, field: str, field_values: list[Any]) -> str:
        if isinstance(field_values[0], str):
            field_values_query = ','.join(
                [f'"{value}"' for value in field_values])
        else:
            field_values_query = ','.join(
                [str(value) for value in field_values])

        query = WHERE_CLAUSE_TEMPLATE.format(
            field=field,
            field_values_query=field_values_query
        )
        return query

    def create_order_by_clause(self, field: str, order: int) -> str:
        return field + ' ASC' if order else ' DESC'

    def get_shifts(
        self,
        min_dttm: str,
        table_name: str = "shifts_available_new",
        field_filter: dict[str, list[Any]] = {},
        order_by: list[list[Any]] = [],
        limit: int = 0
    ) -> list[dict[str, Any]]:

        columns = ["user_id", "data", "username",
                   "employee_type", "week_number"]
        query = self.create_select_query(
            table_name=table_name,
            columns=columns,
            field_filter=field_filter,
            order_by=order_by,
            limit=limit,
            min_dttm=min_dttm
        )

        logger.info(query)

        result = self.execute_query(query)
        result_parsed: list[dict] = []
        try:
            if result:
                result_parsed = [self.parse_row(
                    row, columns) for row in result]
        except Exception:
            logger.exception("Error while executing query", exc_info=True)

        return result_parsed

    def insert_shifts(self, user_id: int, username: str, created_at: str, week_number: str, data: str, employee_type: EmployeeType, table_name: str) -> list[dict]:
        tbl: Table = Table(table_name)

        query = SQLLiteQuery.into(tbl).columns(
            tbl.user_id, tbl.username, tbl.created_at, tbl.week_number, tbl.data, tbl.employee_type
        ).insert(user_id, username, created_at, week_number, data, employee_type)
        q = self.on_conflict_replace(query)

        logger.info(q)

        return self.execute_query(q)

    def on_conflict_replace(self, query: QueryBuilder) -> str:
        q = query.get_sql().replace("INSERT", "INSERT OR REPLACE")
        return q
