from datetime import timedelta
from email.mime import application

from arrow import arrow
from dotenv import load_dotenv
import logging
import os


from datasource.sqlite.sqlite import SQLiteDataBase
from service.service import Service
from persistence.ydb_persistence import YdbPersistence

from telegram.ext import Application
from telegram import Update

import handlers
from handlers.error_handler import error_handler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)


load_dotenv()


async def cleanup_old_records(context, db_path: str = os.environ.get("DB_PATH")):
    """Удаляет записи старше 3 месяцев. Вызывается JobQueue."""
    cutoff_date = arrow.utcnow().shift(months=-3).isoformat()

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "DELETE FROM measurements WHERE created_at < ?",
            (cutoff_date,)
        )
        await db.commit()
        logging.info(f"Удалено старых записей: {cursor.rowcount}")


def main() -> None:
    TG_TOKEN: str | None = os.environ.get("BOT_TOKEN")
    if not TG_TOKEN:
        raise ValueError("TG_TOKEN is not set")

    db_path = os.environ.get("DB_PATH")
    if not db_path:
        raise ValueError("DB_PATH is not set")

    db = SQLiteDataBase(path=db_path)
    service = Service(db=db)
    shift_button_handler = handlers.SendShiftsHandler(service=service)
    shift_chooser_handler = handlers.new_shift_chooser_handler(
        shift_button_handler)

    handlers_list = [
        handlers.start_handler,

        shift_chooser_handler,
        handlers.ScheduleCreateHandler(service=service),

        handlers.forward_message_handler,
        handlers.slots_update_handler
    ]

    application = (Application
                   .builder()
                   .token(TG_TOKEN)
                   .pool_timeout(100)
                   .connect_timeout(100)
                   .connection_pool_size(1000)
                   .build())

    job_queue = application.job_queue

    # Запускать каждые 24 часа, первый запуск — сразу при старте бота
    job_queue.run_repeating(
        cleanup_old_records,
        interval=timedelta(days=1),
        # первый запуск через 10 секунд после старта (можно поставить 0)
        first=10,
    )

    application.add_handlers(handlers=handlers_list)
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
