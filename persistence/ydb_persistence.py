import json
import logging
from typing import Any, Dict
from telegram.ext import BasePersistence
from telegram.ext._basepersistence import PersistenceInput
from typing import Tuple, List

from datasource import YDocTableController
from datasource.models import UserData, ConversationData

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class YdbPersistence(BasePersistence):
    def __init__(self, db: YDocTableController,  store_data: PersistenceInput | None = None, update_interval: float = 60):
        if not store_data:
            store_data = PersistenceInput(
                bot_data=False, chat_data=False, callback_data=False)

        super().__init__(store_data, update_interval)
        self.db = db

    async def get_user_data(self) -> dict[int, dict]:
        data = self.db.get_user_data()
        user_data = self.db_to_user_data(data)
        return user_data

    def db_to_user_data(self, rows: List["UserData"]) -> dict[int, dict]:
        return {
            r.user_id: r.model_dump()
            for r in rows
        }

    async def update_user_data(self, user_id: int, data: dict) -> None:
        if not data:
            return

        data['user_id'] = user_id
        logger.info(f'Updating user data via persistence: {user_id}={data}')
        user_data = UserData(**data)
        self.db.update_user_data(user_data)

    async def refresh_user_data(self, user_id: int, user_data: dict) -> None:
        await self.update_user_data(user_id, user_data)

    async def drop_user_data(self, user_id: int) -> None:
        self.db.delete_user_data(user_id)

    async def get_conversations(self, name: str) -> dict:
        rows = self.db.get_conversations(conversation_name=name)
        if rows:
            conv_data = self.conversation_to_dict(rows)
            return conv_data

        return {}

    def conversation_to_dict(self, rows: List["ConversationData"]) -> dict[Tuple[int | str, ...], object | None]:
        return {
            row.key: row.state
            for row in rows
        }

    async def update_conversation(self, name: str, key: Tuple[int | str, ...], new_state: object | None) -> None:
        conv_data = ConversationData(
            conversation_name=name, key=key, state=new_state)
        self.db.update_conversation(conv_data)

    async def get_bot_data(self) -> None:
        pass

    async def update_bot_data(self, data: dict) -> None:
        pass

    async def refresh_bot_data(self, bot_data: dict) -> None:
        pass

    async def get_chat_data(self) -> None:
        pass

    async def update_chat_data(self, chat_id: int, data: dict) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: dict) -> None:
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def get_callback_data(self) -> Tuple[List[Tuple[str, float, Dict[str, Any]]], Dict[str, str]] | None:
        pass

    async def update_callback_data(self, data: Tuple[List[Tuple[str, float, Dict[str, Any]]], Dict[str, str]]) -> None:
        pass

    async def flush(self) -> None:
        pass
