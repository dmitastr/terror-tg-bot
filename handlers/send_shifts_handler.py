import logging
from typing import Any, Dict, List, Tuple

import arrow
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram._utils.defaultvalue import DEFAULT_TRUE
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters, BaseHandler
from telegram.constants import ParseMode

from service.service import Service
from common.config import DEV_USER_ID, SLOTS
from common.utils import flatten_length

from datasource import gm_database, slots_database, EmployeeType
from datasource.models.gm import GameMaster

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

day_names = {
    "1": ("Пн", 0),
    "2": ("Вт", 0),
    "3": ("Ср", 1),
    "4": ("Чт", 1),
    "5": ("Пт", 2),
    "6": ("Сб", 3),
    "7": ("Вс", 4),
}

period_names = {
    "1": ("утро", 0),
    "3": ("вечер", 1),
    "4": ("15-21", 1),
    "5": ("ночь", 2),
}

other_names = {
    'submit': ('Отправить', 6, 0, '99'),
    'comment': ('Комментарий', 5, 1, '98'),
    'all': ('Выбрать все', 5, 0, '97')
}


def get_longest_keyboard(gms: List[GameMaster], selected_opts: Dict[str, Any]) -> InlineKeyboardMarkup:
    keyboards = [
        get_keyboard(emp_type=gm.employee_type,
                     selected=selected_opts)
        for gm in gms
    ]

    maxKeyboardIdx = keyboards.index(
        max(keyboards, key=lambda kb: flatten_length(kb.inline_keyboard)))

    return keyboards[maxKeyboardIdx]


class Button:
    def __init__(self, id: str) -> None:
        if name := other_names.get(id):
            self.id = name[3]
            self.name = name[0]
            self.position = (name[1], name[2])
        else:
            self.id = id
            day = id[0]
            period = id[1]
            self.name = f"{day_names[day][0]} {period_names[period][0]}"
            self.position = self.calculate_position(day, period)
        self.callback_data = id

    def to_keyboard_button(self, check_type: int = 0) -> InlineKeyboardButton:
        suffix = ''
        match check_type:
            case 0:
                suffix = ' 🟢'
            case 1:
                suffix = ' 🟡'

        name = self.name + suffix
        return InlineKeyboardButton(name, callback_data=self.callback_data)

    def calculate_position(self, day: str, period: str) -> Tuple[int, int]:
        return (day_names[day][1], period_names[period][1])


def buttons_for_type(emp_type: EmployeeType) -> List[Button]:
    buttons: List[Button] = [
        Button(slot) for slot in sorted(slots_database.as_list(emp_type=emp_type))]
    buttons += [Button('submit'), Button('comment'), Button('all'),]

    return buttons


# buttons: List[Button] = [Button(slot) for slot in SLOTS]


CHECK_CAN: int = 0
CHECK_WANT: int = 1
UNCHECK: int = 2

CHOICE, COMMENT = range(2)

USER_DATA: dict[str, Any] = {}


class Keyboard:
    def __init__(self, buttons: List[Button]) -> None:
        self.buttons = buttons

    def create_keyboard(self, selected: dict[str, List[str]] = {}) -> List[List[InlineKeyboardButton]]:
        row_limit = 3
        buttons = sorted(self.buttons, key=lambda x: x.id)
        keyboard = [[] for _ in range(buttons[-1].position[0]+1)]

        keyboard: List[List[InlineKeyboardButton]] = []
        row_buttons: List[InlineKeyboardButton] = []

        buttons_low = [b for b in buttons if b.id == '99']
        buttons_mid = [b for b in buttons if b.id >= '97' and b.id < '99']
        buttons_high = [b for b in buttons if b.id < '90']

        for btn in buttons_high:
            check_type = 2
            if btn.callback_data in selected.get('wants', []):
                check_type = 0
            elif btn.callback_data in selected.get('cans', []):
                check_type = 1

            row_buttons.append(btn.to_keyboard_button(check_type))
            if len(row_buttons) == row_limit:
                keyboard.append(row_buttons)
                row_buttons: List[InlineKeyboardButton] = []

        if row_buttons:
            keyboard.append(row_buttons)

        keyboard.append([b.to_keyboard_button(2) for b in buttons_mid])
        keyboard.append([b.to_keyboard_button(2) for b in buttons_low])

        return keyboard


def get_keyboard(emp_type: EmployeeType, selected: dict[str, List[str]] = {}):
    buttons = buttons_for_type(emp_type=emp_type)
    keyboard = Keyboard(buttons).create_keyboard(selected)

    return InlineKeyboardMarkup(keyboard)


def names_generate(shifts: List[str]) -> str:
    txt: List[str] = []
    for shift in shifts:
        btn = Button(shift)
        txt.append(btn.name)
    return ', '.join(txt)


def choices_update(choices: dict[str, List[str]], new_choice: str) -> dict[str, List[str]]:
    if not choices.get('wants'):
        choices['wants'] = []
    if not choices.get('cans'):
        choices['cans'] = []

    if new_choice == 'all':
        if len(choices['wants']) == len(SLOTS):
            choices['wants'] = []
        else:
            choices['wants'] = SLOTS

        choices['cans'] = []
        return choices

    if new_choice in choices['cans']:
        choices['cans'].remove(new_choice)
    elif new_choice in choices['wants']:
        choices['wants'].remove(new_choice)
        choices['cans'].append(new_choice)
    else:
        choices['wants'].append(new_choice)

    return choices


def get_username(update: Update) -> str:
    if not update.effective_user:
        return "UNKNOWN"

    username: str = update.effective_user.username or str(
        update.effective_user.id)
    username = username.lower()
    return username

# handler funcs


async def send_shift_choices(update: Update, context: CallbackContext) -> int:
    if not isinstance(context.user_data, dict) or not update.effective_message:
        return ConversationHandler.END

    username: str = get_username(update)
    gms = gm_database.get_by_id_all(update.effective_user.id)
    if not gms:
        await update.effective_message.reply_text("Несанкционированный доступ! Ожидайте добавления в базу")
        return ConversationHandler.END

    context.user_data['selected_options'] = {
        'cans': [], 'wants': [], 'comment': ''}
    context.user_data['username'] = username

    keyboard = get_longest_keyboard(
        gms=gms, selected_opts=context.user_data.get('selected_options', {}))

    await update.effective_message.reply_text('Отметь подходящие варианты', reply_markup=keyboard)
    return CHOICE


async def add_comment(update: Update, context: CallbackContext) -> int:
    logger.info("add comment to shifts")
    if update.effective_message and isinstance(context.user_data, dict):
        context.user_data['selected_options']['comment'] = update.effective_message.text
        logger.info(f"comment: {update.effective_message.text}")

        gms = gm_database.get_by_id_all(update.effective_user.id)

        keyboard = get_longest_keyboard(
            gms=gms, selected_opts=context.user_data.get('selected_options', {}))

    await update.effective_message.reply_text('Отметь подходящие варианты', reply_markup=keyboard)

    return CHOICE


async def cancel(update: Update, context: CallbackContext) -> int:
    if update.message:
        if user := update.message.from_user:
            logger.info("User %s canceled the conversation.", user.id)
        await update.message.reply_text("Отмена", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


class SendShiftsHandler(BaseHandler):
    def __init__(self, service: Service):
        self.service = service
        self.block = True

    def save_shifts(self, user_data: Dict[str, Any]) -> None:
        return self.service.save_shifts(user_data)

    def check_update(self, update: object) -> Any:
        return isinstance(update, Update) and update.callback_query

    async def handle_update(self, update: Update, application: Application, check_result: bool | None, context: CallbackContext) -> int:
        query: CallbackQuery = update.callback_query
        if not query:
            return ConversationHandler.END

        await query.answer()

        username: str = get_username(update)

        gms: List[GameMaster] = gm_database.get_by_id_all(
            update.effective_user.id)
        if not gms:
            return ConversationHandler.END

        logger.info(f"Receive callback query: {query}")
        if not isinstance(context.user_data, dict) or not query.data:
            return ConversationHandler.END

        selected_options = context.user_data.get('selected_options', {})

        is_sent = False
        choice = query.data
        if choice == 'submit':
            for gm in gms:
                user_data: dict[str, Any] = context.user_data.copy()
                selected_options_upd: dict[str, Any] = user_data.get(
                    'selected_options', {}).copy()

                user_data['save_shifts'] = True
                if update.effective_user:
                    user_id = update.effective_user.id
                    username = str(user_id)
                    if update.effective_user.username:
                        username = update.effective_user.username.lower()

                    user_data['username'] = username
                    user_data['user_id'] = update.effective_user.id
                    user_data['employee_type'] = gm.employee_type

                if not selected_options_upd.get("wants", []):
                    selected_options_upd['wants'] = selected_options_upd.get(
                        'cans', [])
                    selected_options_upd['cans'] = []

                selected_options_upd["comment"] = selected_options_upd.get(
                    "comment", "").replace("\n", "---")

                user_data["selected_options"] = selected_options_upd

                logger.info(
                    f"Saving gm shifts proposal: {user_data}")
                self.save_shifts(user_data)

                text = 'Твои пожелания на следующую неделю:\n'
                if selected_options:
                    if wants := selected_options.get('wants'):
                        text += f'Хочу: {names_generate(wants)}\n'

                    if cans := selected_options.get('cans'):
                        text += f'Могу: {names_generate(cans)}\n'

                else:
                    text = "Ты не выбрал ничего"

                if comment := selected_options['comment']:
                    text += f'\nКомментарий: {comment}'

                if not is_sent:
                    is_sent = True
                    await query.edit_message_text(text)

                admins = gm_database.get_controllers().get_by_type(
                    emp_type=gm.employee_type).as_list()
                for admin in admins:
                    if admin.tg_id != user_data.get("user_id", -1):
                        await context.bot.send_message(
                            chat_id=admin.tg_id,
                            text=f'{gm.name} @{user_data.get('username', 'UNKNOWN')}\n{text}',
                            parse_mode=ParseMode.HTML
                        )
            return ConversationHandler.END

        elif choice == 'comment':
            if update.effective_chat:
                await query.edit_message_text('Напиши комментарий')
            return COMMENT

        selected_options = choices_update(selected_options, query.data)

        context.user_data['selected_options'] = selected_options

        markup = get_longest_keyboard(gms=gms, selected_opts=selected_options)

        await query.edit_message_reply_markup(reply_markup=markup)
        return CHOICE


def new_shift_chooser_handler(callback_query_handler: BaseHandler) -> ConversationHandler:
    conv_start_handler = CommandHandler(
        command='send_shifts', callback=send_shift_choices, filters=filters.ChatType.PRIVATE)

    shift_choose_conversation_handler = ConversationHandler(
        entry_points=[conv_start_handler],
        states={
            CHOICE: [callback_query_handler],
            COMMENT: [MessageHandler(filters.TEXT, add_comment)]
        },
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        fallbacks=[CommandHandler("cancel", cancel)],
        name="sendShifts"
    )
    return shift_choose_conversation_handler
