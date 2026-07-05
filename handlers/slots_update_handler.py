import io
import json
import logging
from typing import List

from telegram.ext import (
    CallbackContext,
    CommandHandler,
)
from telegram import (
    Update,
)
from telegram.constants import ParseMode

from datasource.models.slots import Slot, weekdays, period_names

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SlotsParser:
    def parse_slots(self, slots_raw: List[str]) -> List[Slot]:
        employee_type = slots_raw[0].strip().lower()
        slots: List[Slot] = []

        for i in range(1, len(slots_raw), 3):
            try:
                weekday_name, timeperiod_name, capacity = map(
                    str.strip, slots_raw[i:i+3])
                slot_id = 0
                for day, weekday in weekdays.items():
                    if weekday == weekday_name:
                        slot_id += (day+1) * 10
                        break
                for time_period, period_name in period_names.items():
                    if period_name == timeperiod_name:
                        slot_id += time_period
                        break

                slots.append(Slot(id=slot_id, capacity=int(capacity),
                                  employee_type=employee_type))
            except Exception as e:
                logger.error(
                    f"Invalid slot format: {slots_raw[i:i+3]}, Error: {e}")
        return slots


async def slots_update(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        await context.bot.send_message(
            chat_id=update,
            text="Пожалуйста, предоставьте данные в формате: <employee_type> <weekday> <time_period> <capacity>",
            parse_mode=ParseMode.HTML
        )
        return

    slots = SlotsParser().parse_slots(context.args)
    f = io.StringIO()
    json.dump([slot.model_dump()
              for slot in slots], f, ensure_ascii=False, indent=4)

    if slots:
        f.seek(0)
        await update.effective_chat.send_document(
            caption='Новые слоты',
            document=f,
            filename=f"slots_flat.json"
        )

slots_update_handler = CommandHandler(
    ['slots_update'],
    slots_update,
)
