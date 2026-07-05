import json
from typing import Any, List
from pydantic import BaseModel, field_serializer, field_validator, model_serializer, model_validator

# "{\"selected_options\": {\"cans\": [], \"wants\": [], \"comment\": \"\"}, \"save_shifts\": true, \"username\": \"Milkymarss\", \"user_id\": 468478472}"


class SelectedOptions(BaseModel):
    cans: List[str] = []
    wants: List[str] = []
    comment: str = ''

    @field_validator("cans", "wants", mode="before")
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON for tags field")
        return v

    # @field_serializer("cans", "wants")
    # def list_to_json(self, lst: List[str]):
    #     return json.dumps(lst)


class UserData(BaseModel):
    user_id: int
    selected_options: SelectedOptions = {}
    save_shifts: bool = True
    username: str = 'UNKNOWN'

    def to_flat_dict(self, key_prefix: str = '') -> dict[str, Any]:
        model_dump = self.model_dump()
        opts = model_dump.pop('selected_options')
        model_dump["cans"] = json.dumps(opts['cans'])
        model_dump["wants"] = json.dumps(opts['wants'])
        model_dump["comment"] = opts["comment"]
        return {
            **{f"{key_prefix}{k}": v for k, v in model_dump.items()},
        }

    @model_validator(mode="before")
    def build_selected_opts(cls, values: dict[str, Any]):
        if values.get("selected_options"):
            return values

        values["selected_options"] = {
            "cans": values.pop("cans", None),
            "wants": values.pop("wants", None),
            "comment": values.pop("comment", None),
        }
        return values
