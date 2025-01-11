import os.path
import json
from os import mkdir, path
from copy import deepcopy

from comguard.constants import FOLDER_DATA, FILE_SUFFIX
from comguard.debug import Debug

TODAY_DATA = "Today Data"
YESTERDAY_DATA = "Yesterday Data"

class DataManager:
    """
    Keep Track of user's daily activities (CMDR agnostic)
    """
    def __init__(self, comguard):
        self.Comguard = comguard

        self.TodayData = {}
        self.YesterdayData = {}


    def load(self):
        file = path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{TODAY_DATA}{FILE_SUFFIX}")
        if path.exists(file):
            with open(file) as json_file:
                self.TodayData = json.load(json_file)
                z = len(self.TodayData)
                for i in range(1, z + 1):
                    x = str(i)
                    self.TodayData[i] = self.TodayData[x]
                    del self.TodayData[x]
        file = path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{YESTERDAY_DATA}{FILE_SUFFIX}")
        if path.exists(file):
            with open(file) as json_file:
                self.YesterdayData = json.load(json_file)
                z = len(self.YesterdayData)
                for i in range(1, z + 1):
                    x = str(i)
                    self.YesterdayData[i] = self.YesterdayData[x]
                    del self.YesterdayData[x]


    def save(self):
        file = path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{TODAY_DATA}{FILE_SUFFIX}")
        with open(file, 'w') as outfile:
            json.dump(self.TodayData, outfile)
        file = path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{YESTERDAY_DATA}{FILE_SUFFIX}")
        with open(file, 'w') as outfile:
            json.dump(self.YesterdayData, outfile)


    def zeroize(self):
        file = path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{TODAY_DATA}{FILE_SUFFIX}")
        with open(file, 'w') as outfile:
            json.dump({}, outfile)
        file = path.join(self.Comguard.plugin_dir, FOLDER_DATA, f"{YESTERDAY_DATA}{FILE_SUFFIX}")
        with open(file, 'w') as outfile:
            json.dump({}, outfile)


    def add_tally_by_system(self, system, faction, column, value):
            """
            Add the value to the system > Faction > Column entry based on systemName
            """
            for y in self.TodayData:
                if system == self.TodayData[y][0]['System']:
                    for z in range(0, len(self.TodayData[y][0]['Factions'])):
                        if faction == self.TodayData[y][0]['Factions'][z]['Faction']:
                            self.TodayData[y][0]['Factions'][z][column] += value
                            break
                    break


    def get_system_from_address(self, systemAddress):
        """
        Return the system name (if found) based on the systemAddress (for missions)
        """
        systemName = None
        for y in self.TodayData:
            if systemAddress == self.TodayData[y][0]['SystemAddress']:
                systemName = self.TodayData[y][0]['System']
                break

        return systemName
    
    def get_index_from_systemAddress(self, systemAddress):
        """
        Return the data index (if found) from a system Address
        """
        index = 0
        for y in self.TodayData:
            if systemAddress == self.TodayData[y][0]['SystemAddress']:
                return y

        return index
    

    def populate_system_data(self, entry):
        Debug.logger.debug("populate system data")
        factionNames = []
        factionStates = []
        z = 0
        #Only process inhabited systems
        for i in entry['Factions']:
            if i['Name'] != "Pilots' Federation Local Branch":
                factionNames.append(i['Name'])
                factionStates.append({'Faction': i['Name'], 'State': i['FactionState']})
                z += 1
        x = len(self.TodayData)
        if (x >= 1):
            for y in range(1, x + 1):
                if entry['StarSystem'] == self.TodayData[y][0]['System']:
                    return
            self.TodayData[x + 1] = [
                {'System': entry['StarSystem'], 'SystemAddress': entry['SystemAddress'], 'Factions': []}]
            z = len(factionNames)
            for i in range(0, z):
                self.TodayData[x + 1][0]['Factions'].append(
                    {'Faction': factionNames[i], 'FactionState': factionStates[i]['State'],
                        'MissionPoints': 0,
                        'TradeProfit': 0, 'Bounties': 0, 'CartData': 0,
                        'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0})
        else:
            self.TodayData = {
                1: [{'System': entry['StarSystem'], 'SystemAddress': entry['SystemAddress'], 'Factions': []}]}
            z = len(factionNames)
            for i in range(0, z):
                self.TodayData[1][0]['Factions'].append(
                    {'Faction': factionNames[i], 'FactionState': factionStates[i]['State'],
                        'MissionPoints': 0,
                        'TradeProfit': 0, 'Bounties': 0, 'CartData': 0,
                        'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0})
                
    def tick_rollover(self):
        Debug.logger.info('New tick detected')
        systemIndex = self.get_index_from_systemAddress(self.Comguard.CmdrManager.get_system())
        self.YesterdayData = deepcopy(self.TodayData)
        # Save current system and reset to 0 if applicable
        try:
            currentData = self.TodayData[systemIndex]
        except KeyError:
            Debug.logger.info('No data available for curent system')
            self.TodayData = {}
            return
        t = len(currentData[0]['Factions'])
        for z in range(0, t):
            factionName = currentData[0]['Factions'][z]['Faction']
            factionState = currentData[0]['Factions'][z]['FactionState']
            currentData[0]['Factions'][z] = {'Faction': factionName, 'FactionState': factionState,
                    'MissionPoints': 0,
                    'TradeProfit': 0, 'Bounties': 0, 'CartData': 0,
                    'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0}
        self.TodayData = {1: currentData}
        