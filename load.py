import myNotebook as nb
import sys
import json
import requests
import pathlib
from config import config
from theme import theme
import webbrowser
import os.path
from os import path
from copy import deepcopy
import tkinter as tk
from tkinter import ttk
from ttkHyperlinkLabel import HyperlinkLabel
from monitor import monitor
from time import sleep
from threading import Thread

import logging

from config import appname

# This could also be returned from plugin_start3()
plugin_name = os.path.basename(os.path.dirname(__file__))

# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name as per the preceding
#     code, else the logger won't be properly set up.
logger = logging.getLogger(f'{appname}.{plugin_name}')

# If the Logger has handlers then it was already set up by the core code, else
# it needs setting up here.
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()

    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_formatter = logging.Formatter(
        f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

"""
Comguard version
"""
this = sys.modules[__name__]  # For holding module globals
this.VersionNo = "2.1.2"
this.ApiVersion = "1.2.0"
this.APIKey = ""
this.APIKeys = []
this.APITest = ""
this.TodayData = {}
this.YesterdayData = {}
this.DataIndex = 0
this.marketData = []
this.marketId = 0
this.Status = "Active"
this.TickTime = ""
this.currentCmdr = ""
this.DoWork = True
this.State = tk.IntVar()
this.MissionLog = []
this.worker = {}

def plugin_prefs(parent, cmdr, is_beta):
    """
    Return a TK Frame for adding to the EDMC settings dialog.
    """
    x_pad = 10
    y_pad = (5, 0)
    x_button_pad = 12

    frame = nb.Frame(parent)
    
    HyperlinkLabel(
        frame,
        text='Comguard',
        background=nb.Label().cget('background'),
        url='https://comguard.app',
        underline=True
    ).grid(columnspan=2, padx=x_pad, sticky=tk.W)  # Don't translate

    nb.Label(frame, text="EDMC Comguard v" + this.VersionNo).grid(columnspan=2, padx=x_pad, sticky=tk.W)

    nb.Checkbutton(frame, text="Send BGS activity to Comguard", variable=this.Status, onvalue="Active",
                   offvalue="Paused").grid(columnspan=2, pady=y_pad, padx=x_button_pad, sticky=tk.W)
    
    nb.Label(frame).grid(sticky=tk.W)  # big spacer
    
    HyperlinkLabel(
        frame,
        text='Comguard credentials',
        background=nb.Label().cget('background'),
        url='https://comguard.app/profile.php',
        underline=True
    ).grid(columnspan=2, padx=x_pad, sticky=tk.W)  # Don't translate

    nb.Label(frame, text="API Key").grid(column=0, row=6, padx=x_pad, pady=y_pad, sticky=tk.W)
    APIkey = nb.Entry(frame, textvariable=this.APIKey, width=64).grid(column=1, row=6, padx=x_button_pad, pady=y_pad, sticky=tk.W)

    nb.Button(frame, text=_("Test API"), command=test_api).grid(
        sticky=tk.E, row=6, column=2, padx=x_pad, pady=y_pad
    )
    nb.Label(frame, textvariable=this.APITest).grid(columnspan=2, column=1, row=7, padx=x_pad, pady=y_pad, sticky=tk.E)

    return frame


def prefs_changed(cmdr, is_beta):
    """
    Save settings.
    """
    
    found = False
    for cmdrKeys in this.APIKeys:
        if(cmdrKeys['name'] == cmdr):
            found = True
            cmdrKeys['apiKey'] = this.APIKey.get()
            continue

    if(found != True):
        commander = { "name" : cmdr, "apiKey" : this.APIKey.get() } 
        logger.info("Adding commander.")
        this.APIKeys.append(commander)

    save_config()
    this.StatusLabel["text"] = this.Status.get()


def plugin_start(plugin_dir):
    """
    Load this plugin into EDMC
    """
    logger.info("Starting plugin.")
    this.Dir = plugin_dir
    file = os.path.join(this.Dir, "Today Data.json")
    if path.exists(file):
        with open(file) as json_file:
            this.TodayData = json.load(json_file)
            z = len(this.TodayData)
            for i in range(1, z + 1):
                x = str(i)
                this.TodayData[i] = this.TodayData[x]
                del this.TodayData[x]
    file = os.path.join(this.Dir, "Yesterday Data.json")
    if path.exists(file):
        with open(file) as json_file:
            this.YesterdayData = json.load(json_file)
            z = len(this.YesterdayData)
            for i in range(1, z + 1):
                x = str(i)
                this.YesterdayData[i] = this.YesterdayData[x]
                del this.YesterdayData[x]
    file = os.path.join(this.Dir, "MissionLog.json")
    if path.exists(file):
        with open(file) as json_file:
            this.MissionLog = json.load(json_file)
    this.LastTick = tk.StringVar(value=config.get_str("comguard_LastTick"))
    this.TickTime = tk.StringVar(value=config.get_str("comguard_TickTime"))
    this.Status = tk.StringVar(value=config.get_str("comguard_Status"))
    this.DataIndex = tk.IntVar(value=config.get_int("comguard_Index"))
    this.StationFaction = tk.StringVar(value=config.get_str("comguard_Station"))
    this.APIKey = tk.StringVar(value=config.get_str("comguard_APIKey"))
    # Load the per-CMDR array of API keys. The above line loads the last one as EDMC was shut down
    if(config.get_str("comguard_APIKeys") != None and config.get_str("comguard_APIKeys") != "" ):
        this.APIKeys = json.loads(config.get_str("comguard_APIKeys"))
    this.APITest = tk.StringVar(value="")
    try:
        response = requests.get("https://api.github.com/repos/cluster-fox/EDMC-Comguard/releases/latest", timeout=5)  # check latest version
    except requests.exceptions.Timeout:
        logger.warning('Github request timed out')
    else:
        latest = response.json()
        logger.debug(latest)
    try:
        this.GitVersion = latest['tag_name']
    except KeyError:
        logger.info('no tag')
        this.GitVersion = '1.0.0'
    #  tick check, no counter reset
    #  App window is not created yet
    check_tick(0)
    return "Comguard"


def check_tick(update_frame):
    #  tick check and counter reset
    logger.info("Checking tick.")
    try:
        response = requests.get('https://elitebgs.app/api/ebgs/v5/ticks', timeout=5)  # get current tick and reset if changed
    except requests.exceptions.Timeout:
        logger.warning('Elite BGS tick API timed out')
    else:
        tick = response.json()
        this.CurrentTick = tick[0]['_id']
        this.TickTime = tick[0]['time']
        if this.LastTick.get() != this.CurrentTick:
            logger.info('New tick detected')
            this.LastTick.set(this.CurrentTick)
            this.YesterdayData = deepcopy(this.TodayData)
            # Save current system and reset to 0 if applicable
            try:
                currentData = this.TodayData[this.DataIndex.get()]
            except KeyError:
                logger.info('No data available for curent system')
                this.TodayData = {} # Old behaviour - DataIndex might need a reset
                return
            t = len(currentData[0]['Factions'])
            for z in range(0, t):
                factionName = currentData[0]['Factions'][z]['Faction']
                factionState = currentData[0]['Factions'][z]['FactionState']
                currentData[0]['Factions'][z] = {'Faction': factionName, 'FactionState': factionState,
                        'MissionPoints': 0,
                        'TradeProfit': 0, 'Bounties': 0, 'CartData': 0,
                        'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0}
            this.DataIndex.set(1)
            this.TodayData = {1: currentData}
            if update_frame == 1:
                this.TimeLabel = tk.Label(this.frame, text=tick_format(this.TickTime)).grid(row=3, column=1, sticky=tk.W)
                theme.update(this.frame)


def plugin_start3(plugin_dir):
    logger.info("Starting plugin " + os.path.basename(os.path.dirname(__file__)) )
    this.worker = Thread(target = monitor_cmdr)
    this.worker.start()
    return plugin_start(plugin_dir)


def plugin_stop():
    """
    EDMC is closing
    """
    logger.info("Shutting down CMDR monitor")
    this.DoWork = False
    logger.info("Cleaning up")
    save_config()
    clean_missions()
    save_data()


def plugin_app(parent):
    """
    Create a frame for the EDMC main window
    """
    logger.info("Plugin app")  
    this.frame = tk.Frame(parent)
    Title = tk.Label(this.frame, text="EDMC Comguard v" + this.VersionNo)
    Title.grid(row=0, column=0, sticky=tk.W)
    if version_tuple(this.GitVersion) > version_tuple(this.VersionNo):
        title2 = tk.Label(this.frame, text="New version available", fg="blue", cursor="hand2")
        title2.grid(row=0, column=1, sticky=tk.W, )
        title2.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/cluster-fox/EDMC-Comguard/releases"))
    tk.Button(this.frame, text='Data Today', command=display_todaydata).grid(row=1, column=0, padx=3)
    tk.Button(this.frame, text='Data Yesterday', command=display_yesterdaydata).grid(row=1, column=1, padx=3)
    tk.Label(this.frame, text="Status:").grid(row=2, column=0, sticky=tk.W)
    tk.Label(this.frame, text="Last Tick:").grid(row=3, column=0, sticky=tk.W)
    this.StatusLabel = tk.Label(this.frame, text=this.Status.get())
    this.StatusLabel.grid(row=2, column=1, sticky=tk.W)
    this.TimeLabel = tk.Label(this.frame, text=tick_format(this.TickTime)).grid(row=3, column=1, sticky=tk.W)
    return this.frame


def populate_system_data(entry):
    factionNames = []
    factionStates = []
    z = 0
    #Only process inhabited systems
    for i in entry['Factions']:
        if i['Name'] != "Pilots' Federation Local Branch":
            factionNames.append(i['Name'])
            factionStates.append({'Faction': i['Name'], 'State': i['FactionState']})
            z += 1
    x = len(this.TodayData)
    if (x >= 1):
        for y in range(1, x + 1):
            if entry['StarSystem'] == this.TodayData[y][0]['System']:
                this.DataIndex.set(y)
                return
        this.TodayData[x + 1] = [
            {'System': entry['StarSystem'], 'SystemAddress': entry['SystemAddress'], 'Factions': []}]
        this.DataIndex.set(x + 1)
        z = len(factionNames)
        for i in range(0, z):
            this.TodayData[x + 1][0]['Factions'].append(
                {'Faction': factionNames[i], 'FactionState': factionStates[i]['State'],
                    'MissionPoints': 0,
                    'TradeProfit': 0, 'Bounties': 0, 'CartData': 0,
                    'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0})
    else:
        this.TodayData = {
            1: [{'System': entry['StarSystem'], 'SystemAddress': entry['SystemAddress'], 'Factions': []}]}
        z = len(factionNames)
        this.DataIndex.set(1)
        for i in range(0, z):
            this.TodayData[1][0]['Factions'].append(
                {'Faction': factionNames[i], 'FactionState': factionStates[i]['State'],
                    'MissionPoints': 0,
                    'TradeProfit': 0, 'Bounties': 0, 'CartData': 0,
                    'CombatBonds': 0, 'MissionFailed': 0, 'Murdered': 0})


def load_market(entry):
    """
    Load the Market.json data
    """
    marketID = entry['MarketID']
    if this.marketId != marketID:
        this.marketData = None
        this.marketId = marketID

    journaldir = config.get_str('journaldir')
    if journaldir is None or journaldir == '':
        journaldir = config.default_journal_dir

    path = pathlib.Path(journaldir) / f'{entry["event"]}.json'

    with path.open('rb') as f:
        # Don't assume we can definitely stomp entry & entry_name here
        this.marketData = json.load(f)


def get_market_data(commodity, field):
    """
    Iterate through MarketData and find a field value for a commodity
    """
    value = 0
    logger.info(f'Searching for {field} of {commodity} in Market.json')
    for item in this.marketData['Items']:   #Iterate through all items
        if item['Name'] == f'${commodity}_name;':
            value = item[field]
            logger.info(f'Found {commodity}, {field} is {value}')
            break
    
    return value


def add_tally_by_system(system, faction, column, value):
    """
    Add the value to the system > Faction > Column entry based on systemName
    """
    for y in this.TodayData:
        if system == this.TodayData[y][0]['System']:
            for z in range(0, len(this.TodayData[y][0]['Factions'])):
                if faction == this.TodayData[y][0]['Factions'][z]['Faction']:
                    this.TodayData[y][0]['Factions'][z][column] += value
                    break
            break


def get_system_from_address(systemAddress):
    """
    Return the system name (if found) based on the systemAddress (for missions)
    """
    systemName = None
    for y in this.TodayData:
        if systemAddress == this.TodayData[y][0]['SystemAddress']:
            systemName = this.TodayData[y][0]['System']
            break

    return systemName


def journal_entry(cmdr, is_beta, system, station, entry, state):
    """
    Main EDMC Journal Entry Processor Function
    """
    currentSystemAddress = 0
    locationList = ['location', 'fsdjump', 'carrierjump']

    entry_name = entry['event'].lower()
    
    if this.Status.get() != "Active":
        return
    
    if entry_name in locationList:  
        # If event changes the system location, get factions and populate today data
        try:
            test = entry['Factions']
        except KeyError:
            return

        send_data(entry, entry['SystemAddress'], entry['StarSystem'])
        populate_system_data(entry)

    else:
        #Otherwise, check if we have usable tabular data
        try:
            currentSystemAddress = this.TodayData[this.DataIndex.get()][0]['SystemAddress']
        except KeyError:
            pass

    if 'docked' == entry_name:
        this.StationFaction.set(entry['StationFaction']['Name'])  # set controlling faction name
        send_data(entry, currentSystemAddress, system)
        #  tick check and counter reset
        check_tick(1)

    if 'market' == entry_name:
        load_market(entry)
    
    if 'missioncompleted' == entry_name:  # get mission influence value
        missionSystem = system
        missionSystemAddress = currentSystemAddress
        for p in range(len(this.MissionLog)):
            if this.MissionLog[p]["MissionID"] == entry["MissionID"]:
                missionSystem = this.MissionLog[p]['System']
                missionSystemAddress = this.MissionLog[p]['SystemAddress']
                this.MissionLog[p]["Active"] = 0
                break

        send_data(entry, missionSystemAddress, missionSystem)
        
        factionEffects = entry['FactionEffects']
        for i in factionEffects:
            faction = i['Faction']
            if i['Influence'] != []:
                inf = len(i['Influence'][0]['Influence'])
                if i['Influence'][0]['Trend'] == 'DownBad':
                    inf *= -1
                systemName = get_system_from_address(i['Influence'][0]['SystemAddress'])
                add_tally_by_system(systemName, faction, 'MissionPoints', inf)
            else:
                add_tally_by_system(missionSystem, faction, 'MissionPoints', 1)

    if 'sellexplorationdata' == entry_name or "multisellexplorationdata" == entry_name:
        send_data(entry, currentSystemAddress, system, this.StationFaction.get())
        add_tally_by_system(system, this.StationFaction.get(), 'CartData', entry['TotalEarnings'])

    if 'redeemvoucher' == entry_name:
        send_data(entry, currentSystemAddress, system)
        if 'bounty' == entry['Type']:
            for z in entry['Factions']:
                add_tally_by_system(system, z['Faction'], 'Bounties', z['Amount'])
        elif 'CombatBond' == entry['Type']:
            add_tally_by_system(system, entry['Faction'], 'CombatBonds', entry['Amount'])
    
    if 'marketbuy' == entry_name:
        entry['Stock'] = get_market_data(entry['Type'], 'Stock')
        entry['StockBracket'] = get_market_data(entry['Type'], 'StockBracket')
        send_data(entry, currentSystemAddress, system, this.StationFaction.get())

    if 'marketsell' == entry_name:
        entry['Demand'] = get_market_data(entry['Type'], 'Demand')
        entry['DemandBracket'] = get_market_data(entry['Type'], 'DemandBracket')
        send_data(entry, currentSystemAddress, system, this.StationFaction.get())
        profit = entry['TotalSale'] - (entry['Count'] * entry['AvgPricePaid'])
        if 'BlackMarket' in entry:
            profit *= -1  #Black Market is same as a trade loss
        add_tally_by_system(system, this.StationFaction.get(), 'TradeProfit', profit)
    
    if 'missionaccepted' == entry_name:  # mission accepted
        send_data(entry, currentSystemAddress, system)
        this.MissionLog.append({"Name": entry["Name"], "Faction": entry["Faction"], "MissionID": entry["MissionID"], "System": system, "SystemAddress": currentSystemAddress, "Active": 1})
    
    if 'missionfailed' == entry_name:  # mission failed
        for p in range(len(this.MissionLog)):
            if this.MissionLog[p]["MissionID"] == entry["MissionID"]:
                missionSystem = this.MissionLog[p]['System']
                missionFaction = this.MissionLog[p]['Faction']
                send_data(entry, this.MissionLog[p]['SystemAddress'], missionSystem, missionFaction)
                add_tally_by_system(missionSystem, missionFaction, 'MissionFailed', 1)                
                this.MissionLog[p]["Active"] = 0
                break
    
    if 'missionabandoned' == entry_name:
        for p in range(len(this.MissionLog)):
            if this.MissionLog[p]["MissionID"] == entry["MissionID"]:
                this.MissionLog[p]["Active"] = 0
                break
    
    if 'commitcrime' == entry_name:
        if ('murder' == entry['CrimeType']) or ('onFoot_murder' == entry['CrimeType']) or ('assault' == entry['CrimeType']):
            send_data(entry, currentSystemAddress, system)

        if ('murder' == entry['CrimeType']) or ('onFoot_murder' == entry['CrimeType']):
            add_tally_by_system(system, entry['Faction'], 'Murdered', 1)
    
    save_data()


def version_tuple(version):
    try:
        ret = tuple(map(int, version.split(".")))
    except:
        ret = (0,)
    return ret


def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


def display_todaydata():
    display_data(this.TodayData)


def display_yesterdaydata():
    display_data(this.YesterdayData)


def display_data(dataTable):
    form = tk.Toplevel(this.frame)
    form.title("EDMC Comguard v" + this.VersionNo + " - Data Today")
    form.geometry("800x280")
    tab_parent = ttk.Notebook(form)
    for i in dataTable:
        tab = ttk.Frame(tab_parent)
        tab_parent.add(tab, text=dataTable[i][0]['System'])
        FactionLabel = tk.Label(tab, text="Faction")
        FactionStateLabel = tk.Label(tab, text="Faction State")
        MPLabel = tk.Label(tab, text="Misson Points")
        TPLabel = tk.Label(tab, text="Trade Profit")
        BountyLabel = tk.Label(tab, text="Bounties")
        CDLabel = tk.Label(tab, text="Cart Data")
        CombatLabel = tk.Label(tab, text="Combat Bonds")
        FailedLabel = tk.Label(tab, text="Mission Failed")
        MurderLabel = tk.Label(tab, text="Murdered")
        FactionLabel.grid(row=0, column=0)
        FactionStateLabel.grid(row=0, column=1)
        MPLabel.grid(row=0, column=2)
        TPLabel.grid(row=0, column=3)
        BountyLabel.grid(row=0, column=4)
        CDLabel.grid(row=0, column=5)
        CombatLabel.grid(row=0, column=6)
        FailedLabel.grid(row=0, column=7)
        MurderLabel.grid(row=0, column=8)
        z = len(dataTable[i][0]['Factions'])
        for x in range(0, z):
            FactionName = tk.Label(tab, text=dataTable[i][0]['Factions'][x]['Faction'])
            FactionName.grid(row=x + 1, column=0, sticky=tk.W)
            FactionState = tk.Label(tab, text=dataTable[i][0]['Factions'][x]['FactionState'])
            FactionState.grid(row=x + 1, column=1)
            Missions = tk.Label(tab, text=dataTable[i][0]['Factions'][x]['MissionPoints'])
            Missions.grid(row=x + 1, column=2)
            Trade = tk.Label(tab, text=human_format(dataTable[i][0]['Factions'][x]['TradeProfit']))
            Trade.grid(row=x + 1, column=3)
            Bounty = tk.Label(tab, text=human_format(dataTable[i][0]['Factions'][x]['Bounties']))
            Bounty.grid(row=x + 1, column=4)
            CartData = tk.Label(tab, text=human_format(dataTable[i][0]['Factions'][x]['CartData']))
            CartData.grid(row=x + 1, column=5)
            Failed = tk.Label(tab, text=dataTable[i][0]['Factions'][x]['MissionFailed'])
            Failed.grid(row=x + 1, column=7)
            Combat = tk.Label(tab, text=human_format(dataTable[i][0]['Factions'][x]['CombatBonds']))
            Combat.grid(row=x + 1, column=6)
            Murder = tk.Label(tab, text=dataTable[i][0]['Factions'][x]['Murdered'])
            Murder.grid(row=x + 1, column=8)
    tab_parent.pack(expand=1, fill='both')


def tick_format(ticktime):
    datetime1 = ticktime.split('T')
    months = {"01":"Jan", "02":"Feb", "03":"March", "04":"April", "05":"May", "06":"June", "07":"July", "08":"Aug", "09":"Sep", "10":"Oct", "11":"Nov", "12":"Dec"}
    x = datetime1[0]
    z = datetime1[1]
    y = x.split('-')
    date1 = y[2] + " " + months[y[1]]
    time1 = z[0:5]
    datetimetick = time1 + ' UTC ' + date1
    return (datetimetick)


def clean_missions():
    try:
        cleanLog = []
        for x in range(len(this.MissionLog)):
            if this.MissionLog[x]["Active"] == 1:
                cleanLog.append(this.MissionLog[x])
        this.MissionLog = cleanLog
    except:
        return
    return


def save_data():
    config.set('comguard_LastTick', this.CurrentTick)
    config.set('comguard_TickTime', this.TickTime)
    config.set('comguard_Index', this.DataIndex.get())
    config.set('comguard_Station', this.StationFaction.get())
    file = os.path.join(this.Dir, "Today Data.json")
    with open(file, 'w') as outfile:
        json.dump(this.TodayData, outfile)
    file = os.path.join(this.Dir, "Yesterday Data.json")
    with open(file, 'w') as outfile:
        json.dump(this.YesterdayData, outfile)
    file = os.path.join(this.Dir, "MissionLog.json")
    with open(file, 'w') as outfile:
        json.dump(this.MissionLog, outfile)


def save_config():
    config.set('comguard_Status', this.Status.get())
    config.set('comguard_APIKey', this.APIKey.get())
    config.set('comguard_APIKeys', json.dumps(this.APIKeys))


# Remove extra stuff from the events: everything Localized, Extra useless information, etc.
def trim_event(event):
    #jump events are a whitelist to trim most useless information
    jumpWhitelist = ['timestamp', 'event', 'StarSystem', 'SystemAddress', 'Population', 'Factions', 'Conflicts', 'SystemFaction']
    event.pop('Type_Localised', None)
    return event


def send_data(event, systemAddress, systemName, stationFaction = ''):
    apiheaders = {
        "apikey": this.APIKey.get(),
        "apiversion" : this.ApiVersion
    }
    event['tickid'] = this.CurrentTick
    if 'StarSystem' not in event:
        event['StarSystem'] = systemName
    if 'SystemAddress' not in event:
        event['SystemAddress'] = systemAddress
    if (stationFaction != '') and ('StationFaction' not in event) and ('SystemFaction' not in event) and ('Faction' not in event) and ('FactionEffects' not in event) and ('Factions' not in event):
        event['StationFaction'] = {
            "Name": stationFaction
        }
    payload = [event]
    logger.info(json.dumps(payload))
    try:
        response = requests.post(
            url='https://comguard.app/api/events',
            headers=apiheaders,
            json=payload,
            timeout=5
        )
    except requests.exceptions.Timeout:
        logger.warning('Comguard API timed out')
    else:
        logger.info(response)


def test_api():
    this.APITest.set(value="testing")
    apiheaders = {
        "apikey": this.APIKey.get(),
        "apiversion" : this.ApiVersion
    }
    payload = [{
            "timestamp" : "2022-01-01T00:00:00Z",
            "event" : "API test",
            "tickid" : this.CurrentTick,
            "cmdr" : "",
            "StarSystem" : "Tau-3 Gruis",
            "SystemAddress" : 61440246972
        }]
    logger.info(json.dumps(payload))
    try:
        response = requests.post(
            url='https://comguard.app/api/events',
            headers=apiheaders,
            json=payload,
            timeout=5
        )
    except requests.exceptions.Timeout:
        logger.warning('Comguard API timed out')
        this.APITest.set(value="Comguard Server Unavailable")
    else:
        logger.info(response)
        if 200 == response.status_code:
            this.APITest.set(value="Test Successful")
        elif 401 == response.status_code or 403 == response.status_code:
            this.APITest.set(value="Invalid API Key")
        else:
            this.APITest.set(value="Unknown Error")

# Worker needed to monitor the loaded commander name,
# in order to be able to support multiple accounts per user.
def monitor_cmdr():
    while(this.DoWork):
        if(monitor.cmdr != this.currentCmdr):
            found = False 
            for cmdrs in this.APIKeys:
                if(cmdrs['name'] == monitor.cmdr):
                    logger.info("Commander found")
                    this.currentCmdr = monitor.cmdr
                    this.APIKey = tk.StringVar(value = cmdrs['apiKey']) 
                    logger.info(this.APIKey.get())
                    found = True
                    break
            if(False == found):
                this.currentCmdr = monitor.cmdr
                this.APIKey = tk.StringVar(value = '')
        sleep(1)
