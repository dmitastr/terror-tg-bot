import json
from typing import Optional, Tuple
from pydantic import BaseModel, field_validator, model_serializer


class ConversationData(BaseModel):
    conversation_name: str
    key: Tuple[int | str, ...]
    state: Optional[object]

    @field_validator("key", "state", mode="before")
    def parse_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON for tags field")
        return v

    @model_serializer()
    def serialize_model(self):
        return {
            'conversation_name': self.conversation_name,
            'key': json.dumps(self.key),
            'state': json.dumps(self.state),
        }
