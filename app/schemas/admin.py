
from pydantic import BaseModel, ConfigDict, StrictBool


class UserStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_active: StrictBool
