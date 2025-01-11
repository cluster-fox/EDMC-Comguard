import json
from config import config

from comguard.cmdrlocation import CmdrLocation
from comguard.debug import Debug


class CmdrData:
    """
    Hold CMDR data
    """
    def __init__(self, cmdrmanager, cmdrName):
        """
        Create instance
        """
        self.CmdrManager = cmdrmanager

        self.cmdrName: str = cmdrName
        self.Location: CmdrLocation = CmdrLocation(self)
        self.targetData:dict = {}
        self.missionData:list = []


    def set_location(self, locationData:dict):
        self.Location.system = locationData["system"]
        self.Location.faction = locationData["faction"]
        self.Location.fleetCarrier = locationData["fleetcarrier"]
        self.Location.settlement = locationData["settlement"]
        self.Location.conflictZone = locationData["conflictzone"]
        self.Location.megaship = locationData["megaship"]


    def set_missions(self, missions:list):
        self.missionData = missions       


    def get_location(self) -> dict:
        location = {
            "system": self.Location.system,
            "faction": self.Location.faction,
            "fleetcarrier": self.Location.fleetCarrier,
            "settlement": self.Location.settlement,
            "conflictzone": self.Location.conflictZone,
            "megaship": self.Location.megaship,
        }
        return location
    

    def get_missions(self) -> list:
        return self.missionData

