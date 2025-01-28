import json
import os.path
from os import mkdir, path
from config import config
from datetime import datetime, timezone

from comguard.cmdrdata import CmdrData
from comguard.constants import FOLDER_DATA, FILE_SUFFIX
from comguard.debug import Debug

MISSION_LOG = "missionlog"
CMDR_LOCATION = "location"

class CmdrManager:
    """
    Manage CMDR data
    """
    def __init__(self, comguard):
        """
        Create instance
        """
        self.Comguard = comguard

        self.cmdrIndex = 0

        self.cmdrs:list = []
        self.apis:dict[int, dict] = {}
        self.cmdrLibrary: dict = {}

        self.load()

    #Load the cmdr data we have
    def load(self):
        if(config.get_str("comguard_CMDRs") != None and config.get_str("comguard_CMDRs") != "" ):
            self.cmdrs = json.loads(config.get_str("comguard_CMDRs"))

        if(config.get_str("comguard_APIData") != None and config.get_str("comguard_APIData") != "" ):
            #load with typecasting for integer keys
            apiData = json.loads(config.get_str("comguard_APIData"))
            for key in apiData:
                self.apis[int(key)] = apiData[key]

        locationData = {}
        missionData = {}
        
        file = os.path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{MISSION_LOG}{FILE_SUFFIX}")
        if path.exists(file):
            with open(file) as json_file:
                missionData = json.load(json_file)

        file = os.path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{CMDR_LOCATION}{FILE_SUFFIX}")
        if path.exists(file):
            with open(file) as json_file:
                locationData = json.load(json_file)

        #Populate CmdrData
        for key, cmdrValue in enumerate(self.cmdrs):
            self.cmdrLibrary[key] = CmdrData(self, cmdrValue)
            try:
                self.cmdrLibrary[key].set_missions(missionData[str(key)])
                self.cmdrLibrary[key].set_location(locationData[str(key)])
            except KeyError:
                pass
    #TODO : Figure out why faction gets wiped on reload

    #Save the cmdr data we have
    def save(self):
        config.set('comguard_APIData', json.dumps(self.apis))
        config.set('comguard_CMDRs', json.dumps(self.cmdrs))

        locationData = {}
        missionData = {}
        for key in self.cmdrLibrary:
            locationData[key] = self.cmdrLibrary[key].get_location()
            missionData[key] = self.cmdrLibrary[key].get_missions()

        file = os.path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{MISSION_LOG}{FILE_SUFFIX}")
        with open(file, 'w') as outfile:
            json.dump(missionData, outfile)
        
        file = os.path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{CMDR_LOCATION}{FILE_SUFFIX}")
        with open(file, 'w') as outfile:
            json.dump(locationData, outfile)


    def get_cmdr_index(self, cmdrName: str) -> int:
        """
        Returns the CMDR index by name if found, otherwise 0
        """
        try:
            return self.cmdrs.index(cmdrName)
        except ValueError:
            return 0


    #Is bool return really necessary?
    def set_cmdr(self, cmdr) -> bool:
        """
        Set the CMDR to the proper index. If not found, add CMDR
        """
        newCmdr = False
        try:
            i = self.cmdrs.index(cmdr)
        except ValueError:
            self.cmdrs.append(cmdr)
            i = len(self.cmdrs) - 1
            self.cmdrLibrary[i] = CmdrData(self, cmdr)
            newCmdr = True

        self.cmdrIndex = i
        return newCmdr


    def get_cmdr_name(self) -> str:
        try:
            return self.cmdrs[self.cmdrIndex]
        except IndexError:
            return ""

    def get_cmdr(self) -> CmdrData:
        try:
            return self.cmdrLibrary[self.cmdrIndex]
        except IndexError:
            return None        

    def set_system(self, cmdr, strSystem:int):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.system = strSystem

    def set_system_conflicts(self, cmdr, conflicts):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.set_conflicts(conflicts)

    def set_faction(self, cmdr, strFaction:str):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.faction = strFaction

    def set_fleetcarrier(self, cmdr, fc:bool):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.fleetCarrier = fc

    def set_settlement(self, cmdr, dictSettlement:dict):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.settlement = dictSettlement
    
    def set_conflict_zone(self, cmdr, dictCZ:dict):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.conflictZone = dictCZ

    def set_megaship(self, cmdr, dictMegaship:dict):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.megaship = dictMegaship

    def add_mission(self, cmdr, missionId:int, dictMission:dict):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].missionData[missionId] = dictMission

    def add_target(self, cmdr, name, target: dict):
        self.cmdrLibrary[self.get_cmdr_index(cmdr)].targetData[name] = target

#Getters
    def get_system(self, cmdr) -> int:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.system
    
    def get_opponent(self, cmdr, faction) -> str:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.get_opponent(faction)

    def get_faction(self, cmdr) -> str:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.faction

    def get_fleetcarrier(self, cmdr) -> bool:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.fleetCarrier

    def get_settlement(self, cmdr) -> dict:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.settlement
    
    def get_conflict_zone(self, cmdr) -> dict:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.conflictZone

    def get_megaship(self, cmdr) -> dict:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].Location.megaship
    
    def get_mission(self, cmdr, missionId:int) -> dict:
        return self.cmdrLibrary[self.get_cmdr_index(cmdr)].missionData.get(missionId, {})
    
    def get_target(self, cmdr, victim) -> dict | None:
        targetInfo = self.cmdrLibrary[self.get_cmdr_index(cmdr)].targetData.get(victim, None)
        return targetInfo

    def deactivate_mission(self, cmdr, missionId:int):
        if missionId in self.cmdrLibrary[self.get_cmdr_index(cmdr)].missionData:
            self.cmdrLibrary[self.get_cmdr_index(cmdr)].missionData[missionId]['Active'] = False

    def clean_missions(self):
        for key in self.cmdrLibrary:
            for missionId, msn in self.cmdrLibrary[key].missionData.copy().items():
                expired = datetime.now(timezone.utc) > datetime.strptime(f"{msn.get('Expiry', '2020-01-01T00:00:00Z')} +0000", "%Y-%m-%dT%H:%M:%SZ %z")
                if (False == msn["Active"]) or (True == expired):
                    self.cmdrLibrary[key].missionData.pop(missionId, None)


    def zeroize(self):
        self.apis = {}
        self.cmdrs = []
        self.cmdrLibrary = {}
        self.save()
        self.load()
        return


    def get_api_key(self, cmdrName:str) -> str:
        """
        Return the key if api is set, otherwise empty string
        """
        try:
            return self.apis[self.get_cmdr_index(cmdrName)]['key']
        except KeyError:
            return ""
        

    def get_api_active(self, cmdrName:str) -> bool:
        """
        Return True if API is set and active, otherwise false
        """
        try:
            return self.apis[self.get_cmdr_index(cmdrName)]['active']
        except KeyError:
            return False
        

    def set_api(self, cmdrName:str, apiKey:str):
        """
        With empty CMDR list, insert pos 0, otherwise set at proper pos or return
        """
        index: int
        if [] == self.cmdrs: 
            index = 0
        else:
            try:
                index = self.cmdrs.index(cmdrName)
            except ValueError: 
                return
        try:
            if self.apis[index]['key'] == apiKey: 
                return
        except Exception:
            pass
        self.apis[index] = {"key" : apiKey, "active" : False}


    def set_api_active(self, cmdrName:str, active: bool):
        """
        With empty CMDR list, insert pos 0, otherwise set at proper pos or return
        """
        index: int
        if [] == self.cmdrs: 
            index = 0
        else:
            try:
                index = self.cmdrs.index(cmdrName)
            except ValueError: 
                return
        self.apis[index]['active'] = active

