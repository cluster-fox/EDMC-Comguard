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
        self.missionData:dict = {}


    def set_location(self, locationData:dict):
        self.Location.system = locationData["system"]
        self.Location.faction = locationData["faction"]
        self.Location.fleetCarrier = locationData["fleetcarrier"]
        self.Location.settlement = locationData["settlement"]
        self.Location.conflictZone = locationData["conflictzone"]
        self.Location.megaship = locationData["megaship"]
        self.Location.conflicts = locationData["conflicts"]


    def set_missions(self, missions:dict):
        for key, msn in missions:
            self.missionData[int(key)] = msn       


    def get_location(self) -> dict:
        location = {
            "system": self.Location.system,
            "faction": self.Location.faction,
            "fleetcarrier": self.Location.fleetCarrier,
            "settlement": self.Location.settlement,
            "conflictzone": self.Location.conflictZone,
            "megaship": self.Location.megaship,
            "conflicts": self.Location.conflicts
        }
        return location
    

    def get_missions(self) -> dict:
        return self.missionData

