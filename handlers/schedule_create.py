import html
import io
import json
import logging
from random import choice
import string
from prettytable import PrettyTable, TableStyle
from typing import Any, List, Optional, Tuple, Union
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    BaseHandler,
    Application,
    filters
)
from telegram import (
    MessageEntity,
    Update,

)
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from service.service import Service
from gm_schedule_generator.gm_schedule_generator import GmScheduleGenerator
from common.config import DEV_USER_ID, SLOTS
from datasource import gm_database


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def schedule_create(update: Update, context: CallbackContext, message: str | None, schedule_file_content: str | None, available_file_content: str | None) -> None:
    if not update.effective_chat or not update.effective_user:
        return

    if message:
        await update.effective_chat.send_message(text=message, parse_mode=ParseMode.HTML)

    slug: str = ''.join(choice(string.ascii_lowercase) for _ in range(5))

    if schedule_file_content:
        file_schedule = io.StringIO(schedule_file_content)
        await update.effective_chat.send_document(
            caption='Драфт расписания',
            document=file_schedule,
            filename=f"gms_schedule_{slug}.html"
        )

    if available_file_content:
        file_av = io.StringIO(available_file_content)
        await update.effective_chat.send_document(
            caption='Хотелки',
            document=file_av,
            filename=f"gms_av_data_{slug}.html"
        )


schedule_create_handler = CommandHandler(
    ['schedule_create'],
    lambda upd, ctx: 1,
)


class ScheduleCreateHandler(BaseHandler):
    def __init__(self, service: Service):
        self.block = True
        self.service = service
        self.handler = schedule_create_handler
        self.gm_generator = GmScheduleGenerator(service)

    def check_update(self, update: Update) -> Optional[Union[bool, Tuple[List[str], Optional[bool]]]]:
        return self.handler.check_update(update)

    def available_table_create(self, shifts: List[dict[str, Any]]) -> str:
        cols: List[str] = ["name"] + SLOTS
        table: PrettyTable = PrettyTable(field_names=cols, vertical_char="",)
        table.set_style(TableStyle.DEFAULT)

        for shift in shifts:
            row = [shift.get('username')]
            data = shift.get('data', {})
            cans = data.get('cans', [])
            wants = data.get('wants', [])
            for slot in SLOTS:
                val: str = "."
                if slot in cans:
                    val = "i"
                elif slot in wants:
                    val = "I"
                row.append(val)

            table.add_row(row)

        return table.get_string()

    async def handle_update(self, update: Update, application: Application, check_result: Any, context: CallbackContext) -> None:
        username = update.effective_user.username
        admin_gm = gm_database.get_admins().get_by_id(user_id=update.effective_user.id)

        self.handler.collect_additional_context(
            context=context, update=update, application=application, check_result=check_result)
        message = "Извини, но ты не админ (пока)"
        schedule_table = None
        available_table = None

        if admin_gm:
            emp_type = admin_gm.employee_type
            week_number = None
            if len(context.args) == 1:
                week_number = int(context.args[0])
            elif len(context.args) == 2:
                week_number = int(context.args[0])
                emp_type = context.args[1]

            schedule_obj = self.service.schedule_create(
                week_number=week_number, emp_type=emp_type)

            schedule_table = self.gm_generator.render_html_page(
                data=schedule_obj.shifts_filled.shifts_table,
                dates=schedule_obj.shifts_filled.dates,
                alternate=True,
                template_name="table_template.html",
                emp_type=emp_type
            )
            available_table = self.gm_generator.render_html_page(
                data=schedule_obj.availability.availability_table,
                dates=schedule_obj.availability.slots,
                alternate=False,
                template_name="available_shifts.html",
                emp_type=emp_type
            )

            message = ""
            if warnings := schedule_obj.warnings:
                warn_messages: List[str] = [w.get('message') for w in warnings]
                message += f'\n\n**Внимание**\n{"\n".join(warn_messages)}'

        await schedule_create(update, context, message, schedule_table, available_table)


def available_table_create(shifts: List[dict[str, Any]]) -> str:
    cols: List[str] = ["name"] + SLOTS
    table: PrettyTable = PrettyTable(field_names=cols, vertical_char="",)
    table.set_style(TableStyle.DEFAULT)

    for shift in shifts:
        row = [shift.get('username')]
        data = shift.get('data', {})
        cans = data.get('cans', [])
        wants = data.get('wants', [])
        for slot in SLOTS:
            val: str = "."
            if slot in cans:
                val = "i"
            elif slot in wants:
                val = "I"
            row.append(val)

        table.add_row(row)

    return table.get_string()


if __name__ == "__main__":
    shifts = [{"username": "123", "data": {"cans": ["13", "23", "43"]}}]
    table = available_table_create(shifts)
    print(table)
