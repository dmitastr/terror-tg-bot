from typing import List, Optional, Dict
from typing_extensions import Self
from pydantic import BaseModel
from enum import StrEnum


class EmployeeType(StrEnum):
    gamemaster = "gamemaster"
    admin = "admin"


EMP_TYPES: Dict[int, EmployeeType] = {
    40322523: EmployeeType.gamemaster
}


class GameMaster(BaseModel):
    username: str
    name: str
    id: str
    employee_type: EmployeeType
    is_active: bool
    is_admin: bool
    tg_id: int
    is_controller: bool


class GMDatabase(BaseModel):
    GMS: List[GameMaster]

    def get_gm(self, name: str) -> Optional[GameMaster]:
        for gm in self.GMS:
            if gm.name == name:
                return gm
        return None

    def get_by_id(self, user_id: int) -> Optional[GameMaster]:
        for gm in self.GMS:
            if gm.tg_id == user_id:
                return gm
        return None

    def get_by_id_all(self, user_id: int) -> List[GameMaster]:
        return [gm for gm in self.GMS if gm.tg_id == user_id]

    def get_by_username(self, username: str) -> Optional[GameMaster]:
        for gm in self.GMS:
            if gm.username == username:
                return gm
        return None

    def get_active(self) -> Self:
        return GMDatabase(GMS=[gm for gm in self.GMS if gm.is_active])

    def get_by_type(self, emp_type: EmployeeType) -> Self:
        return GMDatabase(GMS=[gm for gm in self.GMS if gm.employee_type == emp_type])

    def as_list(self) -> List[GameMaster]:
        return [gm for gm in self.GMS]

    def get_admins(self) -> Self:
        return GMDatabase(GMS=[gm for gm in self.GMS if gm.is_admin])

    def get_controllers(self) -> Self:
        return GMDatabase(GMS=[gm for gm in self.GMS if gm.is_controller])
