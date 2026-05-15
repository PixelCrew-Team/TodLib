from enum import IntEnum, StrEnum

class FileType(IntEnum):
    FILE = 0
    VOICE = 1
    AUDIO = 2
    VIDEO = 3
    PICTURE = 4
    PROFILE = 5
    PROFILE_THUMBNAIL = 6

class ChatState(StrEnum):
    COMPOSING = "composing"
    PAUSED = "paused"
    ACTIVE = "active"
    GONE = "gone"
    INACTIVE = "inactive"

class MessageType(StrEnum):
    CHAT = "chat"
    GROUPCHAT = "groupchat"
    ERROR = "error"
    HEADLINE = "headline"
    NORMAL = "normal"

class PresenceShow(StrEnum):
    CHAT = "chat"
    AWAY = "away"
    XA = "xa"
    DND = "dnd"