import semantic_version
from companion import SERVER_LIVE, CAPIData
from monitor import monitor

from comguard.api import Api
from comguard.cmdrmanager import CmdrManager
from comguard.constants import CheckStates, FOLDER_DATA
from comguard.datamanager import DataManager
from comguard.debug import Debug
from comguard.requestmanager import RequestManager
from comguard.ui import UI
from comguard.updatemanager import UpdateManager
from comguard.utils import *

import json
import requests
import pathlib
from config import config
import os.path
from os import mkdir, path
import tkinter as tk
from datetime import datetime, timedelta, timezone
from time import sleep
from threading import Thread

from config import appname

CZ_GROUND_LOW_CB_MAX = 5000
CZ_GROUND_MED_CB_MAX = 38000

TIME_WORKER_PERIOD_S = 2

LOCATION_LIST = ['StartUp', 'Location', 'FSDJump', 'CarrierJump']
BODIES_LIST = ['Scan', 'SAASignalsFound']
#Tracked Events, non faction related
TRACKED_LIST = ['ColonisationConstructionDepot', 'ColonisationContribution', 'CargoDepot', 'MiningRefined', 'CollectCargo', 'PowerplayMerits']

class Comguard:
    """
    Main plugin class
    """
    def __init__(self, plugin_name: str, version: semantic_version.Version):
        self.plugin_name:str = plugin_name
        self.version: semantic_version.Version = version

#MAIN FUNCTION START
    def plugin_start(self, plugin_dir: str):

        self.plugin_dir = plugin_dir

        self.debug: Debug = Debug(self)
        Debug.logger.info("Starting plugin " + os.path.basename(os.path.dirname(__file__)) )

        data_filepath = path.join(self.plugin_dir, "data")
        if not path.exists(data_filepath): mkdir(data_filepath)
        
        # Main Classes
        self.CmdrManager: CmdrManager = CmdrManager(self)
        self.DataManager: DataManager = DataManager(self)
        self.Api: Api = Api(self)
        self.Status:tk.StringVar = tk.StringVar(value=config.get_str('Comguard_Status', default=CheckStates.STATE_ON))
        self.Ui: UI = UI(self)
        self.RequestManager: RequestManager = RequestManager(self)
        self.UpdateManager: UpdateManager = UpdateManager(self)

        self.TickTime: str = config.get_str("comguard_TickTime")
        self.Ui.display_tick(self.TickTime)

        self.marketData = {}
        self.marketId = 0

        self.megaship_pat:re.Pattern = re.compile("^[a-z]{3}-[0-9]{3} ")

        self.thread: Thread = Thread(target=self._worker, name="Comguard Main worker")
        self.thread.daemon = True
        self.thread.start()

        """
        Load this plugin into EDMC
        """
        Debug.logger.info("Starting plugin.")

        self.check_tick(True)


#MAIN FUNCTION STOP
    def plugin_stop(self):
        """
        The plugin is shutting down.
        """
        folder = path.join(self.plugin_dir, FOLDER_DATA)
        if not path.exists(folder):
            Debug.logger.info("/data folder not found, creating it")
            mkdir(folder)

        self.save_data()


    def save_data(self):
        self.CmdrManager.clean_missions()
        self.CmdrManager.save()
        self.DataManager.save()
        config.set('comguard_Status', self.Status.get())
        config.set('comguard_TickTime', self.TickTime)

    def zeroize(self):
        config.delete('comguard_Status')
        config.delete('comguard_TickTime')
        self.DataManager.zeroize()
        self.CmdrManager.zeroize()
        
    def _worker(self) -> None:
        """
        Handle thread work
        """
        Debug.logger.debug("Starting Main Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down Main Worker...")
                return

            sleep(TIME_WORKER_PERIOD_S)


    def check_tick(self, update_frame):
        #  tick check and counter reset
        Debug.logger.info("Checking tick.")
        try:
            response = requests.get('http://tick.infomancer.uk/galtick.json', timeout=5)  # get current tick and reset if changed
        except requests.exceptions.Timeout:
            Debug.logger.warning('Elite BGS tick API timed out')
        else:
            tick = response.json()
            ticktime = tick.get('lastGalaxyTick', None)
            if self.TickTime != ticktime:
                self.TickTime = ticktime
                if update_frame == 1:
                    self.Ui.display_tick(self.TickTime)


    def load_market(self, entry):
        """
        Load the Market.json data
        """
        marketID = entry['MarketID']
        if self.marketId != marketID:
            self.marketData = {}
            self.marketId = marketID

        journaldir = config.get_str('journaldir')
        if journaldir is None or journaldir == '':
            journaldir = config.default_journal_dir

        path = pathlib.Path(journaldir) / f'{entry["event"]}.json'

        with path.open('rb') as f:
            jsonData = json.load(f)
            if jsonData:
                self.marketData = jsonData


    def get_market_data(self, commodity, field, default:int=0):
        """
        Iterate through MarketData and find a field value for a commodity
        """
        for item in self.marketData.get('Items', []):   #Iterate through all items
            if item['Name'] == f'${commodity}_name;':
                return item[field]

        Debug.logger.info(f'Could not find {field} of {commodity} in Market.json')
        return default



    def journal_entry(self, cmdr, is_beta, system, station, entry:dict, state):
        """
        Parse an incoming journal entry and store the data we need
        """

        # Live galaxy check
        try:
            if not monitor.is_live_galaxy() or is_beta: return
        except Exception as e:
            Debug.logger.error(f"The EDMC Version is too old, please upgrade to v5.6.0 or later", exc_info=e)
            return
        
        entryName = entry.get('event')

        #We need to set the CMDR in case it's a new one
        self.CmdrManager.set_cmdr(cmdr)

        if self.Status.get() != CheckStates.STATE_ON:
            return
        
        dirty: bool = False

        if entryName in BODIES_LIST:
            self.Api.send_data(cmdr, entry, entry['SystemAddress'], system)

        if entryName in LOCATION_LIST: 
            try:
                test = entry['Factions']
            except KeyError:
                self.Api.send_data(cmdr, entry, entry['SystemAddress'], entry['StarSystem'])
                return

            # If event changes the system location, get factions and populate today data
            self.CmdrManager.set_system(cmdr, entry['SystemAddress'])

            if entry.get('Docked', False) and ('StationFaction' in entry):
                self.CmdrManager.set_faction(cmdr, entry['StationFaction']['Name'])

            self.Api.send_data(cmdr, entry, entry['SystemAddress'], entry['StarSystem'])
            self.CmdrManager.set_system_conflicts(cmdr, entry.get('Conflicts', []))
            self.DataManager.populate_system_data(entry)
            dirty = True
            

        currentSystem = self.CmdrManager.get_system(cmdr)

        if entryName in TRACKED_LIST:
            self.Api.send_data(cmdr, entry, currentSystem, system)

        if 'Docked' == entryName:
            self.Api.send_data(cmdr, entry, currentSystem, system)
            self.CmdrManager.set_faction(cmdr, entry['StationFaction']['Name'])
            dirty = True
            #  tick check and counter reset
            self.check_tick(True)

        stationFaction = self.CmdrManager.get_faction(cmdr)

        if 'Market' == entryName:
            self.load_market(entry)
        
        if 'MissionCompleted' == entryName:  # get mission influence value
            missionSystem = system
            missionSystemAddress = currentSystem
            mission = self.CmdrManager.get_mission(cmdr, entry["MissionID"])
            if {} != mission:
                self.CmdrManager.deactivate_mission(cmdr, entry["MissionID"])
                missionSystem = mission['System']
                missionSystemAddress = mission['SystemAddress']

            self.Api.send_data(cmdr, entry,missionSystemAddress, missionSystem)
            
            factionEffects = entry['FactionEffects']
            for i in factionEffects:
                faction = i['Faction']
                if i['Influence'] != []:
                    inf = len(i['Influence'][0]['Influence'])
                    if i['Influence'][0]['Trend'] == 'DownBad':
                        inf *= -1
                    systemName = self.DataManager.get_system_from_address(i['Influence'][0]['SystemAddress'])
                    self.DataManager.add_tally_by_system(systemName, faction, 'MissionPoints', inf)
                else:
                    self.DataManager.add_tally_by_system(missionSystem, faction, 'MissionPoints', 1)
            dirty = True

        if 'SellExplorationData' == entryName or "MultiSellExplorationData" == entryName:
            self.Api.send_data(cmdr, entry, currentSystem, system, stationFaction)
            
            self.DataManager.add_tally_by_system(system, stationFaction, 'CartData', entry['TotalEarnings'])
            dirty = True

        if 'RedeemVoucher' == entryName:
            self.Api.send_data(cmdr, entry, currentSystem, system)
            
            if 'bounty' == entry['Type']:
                for z in entry['Factions']:
                    self.DataManager.add_tally_by_system(system, z['Faction'], 'Bounties', z['Amount'])
            elif 'CombatBond' == entry['Type']:
                self.DataManager.add_tally_by_system(system, entry['Faction'], 'CombatBonds', entry['Amount'])
            dirty = True

        #MarketBuy
        if 'MarketBuy' == entryName:
            entry['Stock'] = self.get_market_data(entry['Type'], 'Stock', 1000)
            entry['StockBracket'] = self.get_market_data(entry['Type'], 'StockBracket', 2)
            
            self.Api.send_data(cmdr, entry, currentSystem, system, stationFaction)

        #MarketSell
        if 'MarketSell' == entryName:
            entry['Demand'] = self.get_market_data(entry['Type'], 'Demand', 0)
            entry['DemandBracket'] = self.get_market_data(entry['Type'], 'DemandBracket', 2)
            
            self.Api.send_data(cmdr, entry, currentSystem, system, stationFaction)
            
            profit = entry['TotalSale'] - (entry['Count'] * entry['AvgPricePaid'])
            if 'BlackMarket' in entry:
                profit *= -1  #Black Market is same as a trade loss
            self.DataManager.add_tally_by_system(system, stationFaction, 'TradeProfit', profit)
            dirty = True

        if 'MissionAccepted' == entryName:  # mission accepted
            missionId = entry["MissionID"]
            missionData = {
                "Name": entry.get("Name",''), 
                "Faction": entry.get("Faction",''), 
                "System": system, 
                "SystemAddress": currentSystem, 
                "Expiry": entry.get("Expiry", "2020-01-01T00:00:00Z"),
                "Active": 1}
            self.CmdrManager.add_mission(cmdr, missionId, missionData)
            self.Api.send_data(cmdr, entry, currentSystem, system)
            dirty = True
        
        if 'MissionFailed' == entryName:  # mission failed
            missionId = entry["MissionID"]
            mission = self.CmdrManager.get_mission(cmdr, missionId)
            missionSystem = mission.get('System', system)
            missionSystemAddress = mission.get('SystemAddress', currentSystem)
            missionFaction = mission.get('Faction','')
            self.Api.send_data(cmdr, entry, missionSystemAddress, missionSystem, missionFaction)
            if {} != mission:
                self.CmdrManager.deactivate_mission(cmdr, missionId)
                self.DataManager.add_tally_by_system(missionSystem, missionFaction, 'MissionFailed', 1)
            else:
                Debug.logger.debug(f"Mission {missionId} was not found in missionlog and may not record")
            dirty = True
        
        if 'MissionAbandoned' == entryName:
            self.CmdrManager.deactivate_mission(cmdr, entry["MissionID"])
            dirty = True
        
        if 'CommitCrime' == entryName:
            if ('murder' == entry['CrimeType']) or ('onFoot_murder' == entry['CrimeType']) or ('assault' == entry['CrimeType']):
                faction = entry.get('Faction', '')
                victim = entry.get('Victim', None)
                if (victim is not None):
                    targetInfo: dict = self.CmdrManager.get_target(cmdr, victim)
                    if (targetInfo is not None): 
                        faction = targetInfo.get('Faction', faction)
                #Hack to override the faction
                entry['Faction'] = faction
                self.Api.send_data(cmdr, entry, currentSystem, system, faction)
            if ('murder' == entry['CrimeType']) or ('onFoot_murder' == entry['CrimeType']):
                self.DataManager.add_tally_by_system(system, entry['Faction'], 'Murdered', 1)
                dirty = True
        
        if 'Bounty' == entryName:
            megaship: dict = self.CmdrManager.get_megaship(cmdr)
            # Check whether in megaship scenario for scenario tracking
            if megaship != {}:
                timedifference = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(megaship['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
                if timedifference > timedelta(minutes=5):
                    # Too long since we last entered a megaship scenario, we can't be sure we're fighting at that scenario, clear down
                    self.CmdrManager.set_megaship(cmdr, {})
                else:
                    # We're within the timeout, refresh timestamp and handle the CB
                    megaship['timestamp'] = entry['timestamp']
                    self.CmdrManager.set_megaship(cmdr, megaship)
                    self._scenario(cmdr, entry, currentSystem, system)
            dirty = True

        if 'ShipTargeted' == entryName:
            if 'Faction' in entry and 'PilotName_Localised' in entry and 'PilotName' in entry:
                # Store info on targeted ship
                last_ship_targeted = {'Faction': entry['Faction'],
                                            'PilotName': entry['PilotName'],
                                            'PilotName_Localised': entry['PilotName_Localised']}

                if entry['PilotName'].startswith("$ShipName_Police"):
                    self.CmdrManager.add_target(cmdr, entry['PilotName'], last_ship_targeted)
                else:
                    self.CmdrManager.add_target(cmdr, entry['PilotName_Localised'], last_ship_targeted)
            dirty = True

        if ('ApproachSettlement' == entryName) and state['Odyssey']:
            settlement:dict = {'timestamp': entry['timestamp'], 'name': entry['Name'], 'sent': False}
            self.CmdrManager.set_settlement(cmdr, settlement)
            self.CmdrManager.set_megaship(cmdr, {})
            self.CmdrManager.set_conflict_zone(cmdr, {})
            dirty = True

        if ('FactionKillBond' == entryName) and state['Odyssey']:
            settlement: dict = self.CmdrManager.get_settlement(cmdr)
            conflictZone: dict = self.CmdrManager.get_conflict_zone(cmdr)
            if settlement != {}:
                timedifference = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(settlement['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
                if timedifference > timedelta(minutes=5):
                    # Too long since we last approached a settlement, we can't be sure we're fighting at that settlement, clear down
                    self.CmdrManager.set_settlement(cmdr, {})
                    # Fall through to check space CZs too
                else:
                    # We're within the timeout, refresh timestamp and handle the CB
                    settlement['timestamp'] = entry['timestamp']
                    self.CmdrManager.set_settlement(cmdr, settlement)
                    self._ground_cz(cmdr, entry, currentSystem, system)

            elif conflictZone != {}:
                timedifference = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(conflictZone['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
                if timedifference > timedelta(minutes=5):
                    # Too long since we last entered a space cz, we can't be sure we're fighting at that cz, clear down
                    self.CmdrManager.set_conflict_zone(cmdr, {})
                else:
                    # We're within the timeout, refresh timestamp and handle the CB
                    conflictZone['timestamp'] = entry['timestamp']
                    self.CmdrManager.set_conflict_zone(cmdr, conflictZone)
                    self._space_cz(cmdr, entry, currentSystem, system)
            dirty = True

        if 'SupercruiseDestinationDrop' == entryName:
            self.CmdrManager.set_conflict_zone(cmdr, {})
            self.CmdrManager.set_megaship(cmdr, {})
            self.CmdrManager.set_settlement(cmdr, {})
            match entry.get('Type', "").lower():
                case type if type.startswith("$warzone_pointrace_low"):
                    conflictZone: dict = {'timestamp': entry['timestamp'], 'type': 'low', 'sent': False}
                    self.CmdrManager.set_conflict_zone(cmdr, conflictZone)
                case type if type.startswith("$warzone_pointrace_med"):
                    conflictZone: dict = {'timestamp': entry['timestamp'], 'type': 'medium', 'sent': False}
                    self.CmdrManager.set_conflict_zone(cmdr, conflictZone)
                case type if type.startswith("$warzone_pointrace_high"):
                    conflictZone: dict = {'timestamp': entry['timestamp'], 'type': 'high', 'sent': False}
                    self.CmdrManager.set_conflict_zone(cmdr, conflictZone)
                case type if self.megaship_pat.match(type):
                    megaship: dict = {'timestamp': entry['timestamp'], 'sent': False}
                    self.CmdrManager.set_megaship(cmdr, megaship)
            dirty = True


        if 'SupercruiseEntry' == entryName:
            self.CmdrManager.set_settlement(cmdr, {})
            self.CmdrManager.set_megaship(cmdr, {})
            self.CmdrManager.set_conflict_zone(cmdr, {})
            dirty = True

        if dirty:
            self.save_data()


#VERY NEW

    def _ground_cz(self, cmdr, entry:dict, currentSystem:int, system:str):
        """
        Combat bond received while we are in an active ground CZ
        """
        settlement: dict = self.CmdrManager.get_settlement(cmdr)
        if settlement.get('sent', False): return

        if entry['Reward'] < CZ_GROUND_LOW_CB_MAX:
            settlement['size'] = 'low'
            settlement['sent'] = True
        elif entry['Reward'] < CZ_GROUND_MED_CB_MAX:
            settlement['size'] = 'medium'
            settlement['sent'] = True
        else:
            settlement['size'] = 'high'

        event: dict = {
            'event':"SyntheticGroundCZ",
            'timestamp':entry['timestamp'],
            'SystemAddress':currentSystem,
            'Faction':entry.get('AwardingFaction', ""),
            'settlement':settlement['name']
        }
        event[settlement.get('size', 'low')] = 1
        self.Api.send_data(cmdr, event, currentSystem, system)
        settlement['sent'] = True
        self.CmdrManager.set_settlement(cmdr, settlement)
    
    
    def _space_cz(self, cmdr, entry:dict, currentSystem:int, system:str):
        conflict: dict = self.CmdrManager.get_conflict_zone(cmdr)
        if conflict.get('sent', False): return
        
        event: dict = {
            'event':"SyntheticCZ",
            'timestamp':entry['timestamp'],
            'SystemAddress':currentSystem,
            'Faction':entry.get('AwardingFaction', "")
        }
        event[conflict.get('type', 'low')] = 1
        self.Api.send_data(cmdr, event, currentSystem, system)
        conflict['sent'] = True
        self.CmdrManager.set_conflict_zone(cmdr, conflict)


    def _scenario(self, cmdr, entry:dict, currentSystem:int, system:str):
        """
        We are in an active scenario
        """
        megaship:dict = self.CmdrManager.get_megaship(cmdr)
        if megaship.get('sent', False): return

        event: dict = {
            'event':"SyntheticScenario",
            'timestamp':entry['timestamp'],
            'SystemAddress':currentSystem,
            'Faction':self.CmdrManager.get_opponent(cmdr, entry.get('VictimFaction', "")),
            'type':"Megaship",
            'count':1
        }
        self.Api.send_data(cmdr, event, currentSystem, system)
        megaship['sent'] = True
        self.CmdrManager.set_megaship(cmdr, megaship)
