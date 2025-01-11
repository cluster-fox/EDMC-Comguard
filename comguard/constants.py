import sys
from enum import Enum


# Conflict Zones
class CZs(Enum):
    SPACE_HIGH = 0
    SPACE_MED = 1
    SPACE_LOW = 2
    GROUND_HIGH = 3
    GROUND_MED = 4
    GROUND_LOW = 5


# Checkbox states
# Subclassing from str as well as Enum means json.load and json.dump work seamlessly
class CheckStates(str, Enum):
    STATE_OFF = 'Paused'
    STATE_ON = 'Active'
    STATE_PARTIAL = 'Partial'
    STATE_PENDING = 'Pending'


class Ticks(Enum):
    TICK_CURRENT = 0
    TICK_PREVIOUS = 1


class UpdateUIPolicy(Enum):
    NEVER = 0
    IMMEDIATE = 1
    LATER = 2


class FleetCarrierItemType(Enum):
    MATERIALS_SELLING = 0
    MATERIALS_BUYING = 1
    COMMODITIES_SELLING = 2
    COMMODITIES_BUYING = 3


class RequestMethod(Enum):
    GET = 'get'
    POST = 'post'
    PUT = 'put'
    PATCH = 'patch'
    DELETE = 'delete'
    HEAD = 'head'
    OPTIONS = 'options'



DATETIME_FORMAT_JOURNAL: str = "%Y-%m-%dT%H:%M:%SZ"
FILE_SUFFIX: str = ".json"
FOLDER_ASSETS: str = "assets"
FOLDER_BACKUPS: str = "backups"
FOLDER_DATA: str = "data"
#FOLDER_OTHER_DATA: str = "otherdata"
FOLDER_UPDATES: str = "updates"
FONT_HEADING_1: tuple = ("Helvetica", 13, "bold")
FONT_HEADING_2: tuple = ("Helvetica", 11, "bold")
FONT_SMALL: tuple = ("Helvetica", 9, "normal")
if sys.platform == 'win32':
    FONT_TEXT: tuple = ("Segoe UI Emoji", 11, "normal")
    FONT_TEXT_BOLD: tuple = ("Segoe UI Emoji", 11, "bold")
    FONT_TEXT_UNDERLINE: tuple = ("Segoe UI Emoji", 11, "underline")
    FONT_TEXT_BOLD_UNDERLINE: tuple = ("Segoe UI Emoji", 11, "bold underline")
else:
    FONT_TEXT: tuple = ("Helvetica", 11, "normal")
    FONT_TEXT_BOLD: tuple = ("Helvetica", 11, "bold")
    FONT_TEXT_UNDERLINE: tuple = ("Helvetica", 11, "underline")
    FONT_TEXT_BOLD_UNDERLINE: tuple = ("Helvetica", 11, "bold underline")

COLOUR_HEADING_1: str = "#A300A3"
