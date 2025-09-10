from enum import Enum

class Role(str, Enum):
    user = "user"
    mod = "mod"
    admin = "admin"
