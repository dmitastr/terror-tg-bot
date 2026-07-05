# main.py

import io
import logging
import os
from typing import Any, TypedDict, List, Tuple
from jinja2 import Environment, FileSystemLoader

from datasource import EmployeeType

from service.service import Schedule, Service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ScheduleItem(TypedDict):
    gamemaster_name: str
    date: str
    shift: str


class NameItem(TypedDict):
    gamemaster_name: str
    bgcolor: str


class GmScheduleGenerator:
    def __init__(self, service: Service):
        self.service = service

    def render_html_page(self, dates: List[str], data: dict[dict[str, Any]], template_name: str, alternate: bool, emp_type: EmployeeType) -> str:
        """
        Генерирует HTML из данных с помощью Jinja2-шаблона.
        """
        names = self.service.get_gm_human_names(emp_type=emp_type)
        names_with_color = self.color_alternate(names, alternate)

        env = Environment(loader=FileSystemLoader(
            "./gm_schedule_generator/static/templates"))
        template = env.get_template(template_name)

        match emp_type:
            case EmployeeType.gamemaster:
                title = "ИГРОВЕДЫ"
                header_color = "#00ff00"
            case EmployeeType.admin:
                title = "АДМИНИСТРАТОРЫ"
                header_color = "#ff9900"
            case _:
                title = "ГРАФИК"
                header_color = "#00ff00"

        logger.info(dates)
        logger.info(data)
        logger.info(names_with_color)

        return template.render(
            title=title,
            dates=dates,
            names=names_with_color,
            table_data=data,
            header_color=header_color
        )

    def color_alternate(self, names: List[str], alternate: bool) -> List[NameItem]:
        return [
            {'gamemaster_name': name,
             'bgcolor': '#f4cccc' if i % 2 == 0 and alternate else '#ffffff'}
            for i, name in enumerate(names)
        ]

    def normalize_schedule(self, dates: List[str], names: List[str], data: List[ScheduleItem]) -> dict[str, dict[str, str]]:
        """
        Преобразует входные данные в структуру для таблицы.
        Возвращает:
        - список уникальных дат (заголовки колонок)
        - список уникальных гейм-мастеров (заголовки строк)
        - словарь расписания: {имя: {дата: смена}}
        """
        table_data: dict[str, dict[str, str]] = {
            name: {date: "" for date in dates} for name in names}
        for item in data:
            table_data[item["gamemaster_name"]][item["date"]] = item["shift"]

        return table_data

    def render_html_to_image(self, html_content: str) -> Tuple[io.BytesIO, str]:
        img, url = self.hi.html_to_image(html_content)
        return img, url

    def write_file(self, fname: str, data: io.BytesIO):
        with open(fname, 'wb') as f:
            f.write(data.getbuffer())
