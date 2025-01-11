import tkinter as tk
from datetime import datetime, timedelta
from functools import partial
from os import path
from threading import Thread
from time import sleep
from tkinter import PhotoImage, ttk
from tkinter.messagebox import askyesno
from typing import List, Optional

import myNotebook as nb
from ttkHyperlinkLabel import HyperlinkLabel

from config import config

from comguard.constants import FOLDER_ASSETS, FONT_HEADING_2, FONT_SMALL, CheckStates, UpdateUIPolicy
from comguard.debug import Debug
from comguard.utils import human_format, tick_format


TIME_WORKER_PERIOD_S = 2
TIME_TICK_ALERT_M = 60
URL_LATEST_RELEASE = "https://github.com/cluster-fox/EDMC-Comguard/releases/latest"
URL_WEB = "https://comguard.app"
LBL_CONNECT: str = "Activate API"
LBL_DISCONNECT: str = "Disconnect API"
LBL_API_OFF: str = "Disconnected"
LBL_API_ON: str = "API Connected"


class UI:
    """
    Display the user's activity
    """

    def __init__(self, comguard):
        self.Comguard = comguard
        self.frame = None
        
        self.fieldAPIKey: tk.StringVar  = tk.StringVar(value="")
        self.fieldCmdr: tk.StringVar = tk.StringVar(value="")
        self.labelApiConnect: tk.StringVar = tk.StringVar(value=LBL_CONNECT)
        self.APITestStatus: tk.StringVar = tk.StringVar(value=LBL_API_OFF)
        self.TimeLabel: tk.StringVar = tk.StringVar(value="")

        #self.image_logo_comguard_100 = PhotoImage(file = path.join(self.Comguard.plugin_dir, FOLDER_ASSETS, "logo_comguard_100x67.png"))
        #self.image_logo_comguard_16 = PhotoImage(file = path.join(self.Comguard.plugin_dir, FOLDER_ASSETS, "logo_comguard_16x16.png"))
        #self.image_logo_comguard_32 = PhotoImage(file = path.join(self.Comguard.plugin_dir, FOLDER_ASSETS, "logo_comguard_32x32.png"))

        self.thread: Optional[Thread] = Thread(target=self._worker, name="comguard UI worker")
        self.thread.daemon = True
        self.thread.start()



    def get_plugin_frame(self, parent: tk.Frame) -> tk.Frame:
        """
        Create a frame for the EDMC main window
        """        
        self.frame: tk.Frame = tk.Frame(parent)

        current_row: int = 0
        self.title = tk.Label(self.frame, text=f"EDMC Comguard v{str(self.Comguard.version)}")
        self.title.grid(row=current_row, column=0, sticky=tk.W)
        current_row += 1
        tk.Button(self.frame, text='Data Today', command=lambda: self.display_data(self.Comguard.DataManager.TodayData)).grid(row=current_row, column=0, padx=3)
        tk.Button(self.frame, text='Data Yesterday', command=lambda: self.display_data(self.Comguard.DataManager.YesterdayData)).grid(row=current_row, column=1, padx=3)
        current_row += 1
        tk.Label(self.frame, text="Status:").grid(row=current_row, column=0, sticky=tk.W)
        self.StatusLabel = tk.Label(self.frame, text=self.Comguard.Status.get())
        self.StatusLabel.grid(row=current_row, column=1, sticky=tk.W)
        current_row += 1
        tk.Label(self.frame, text="Last Tick:").grid(row=current_row, column=0, sticky=tk.W)
        tk.Label(self.frame, textvariable=self.TimeLabel).grid(row=current_row, column=1, sticky=tk.W)
        return self.frame

#Move UI to object !!
    def get_prefs_frame(self, parent, cmdr):
        """
        Return a TK Frame for adding to the EDMC settings dialog.
        """
        self.plugin_frame:tk.Frame = parent
        frame = nb.Frame(parent)
        # Make the second column fill available space
        frame.columnconfigure(1, weight=1)

        x_pad = 10
        y_pad = (5, 0)
        x_button_pad = 12

        current_row = 1
        nb.Label(frame, text=f"{self.Comguard.plugin_name} v{str(self.Comguard.version)}", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.W)
        HyperlinkLabel(frame, text="Comguard Website", background=nb.Label().cget('background'), url=URL_WEB, underline=True).grid(row=current_row, column=1, padx=10, sticky=tk.W)
        current_row += 1
        
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=10, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Global Settings", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=15, sticky=tk.W) # LANG: Preferences label
        nb.Checkbutton(frame, text=f"{self.Comguard.plugin_name} Active", variable=self.Comguard.Status, onvalue=CheckStates.STATE_ON, offvalue=CheckStates.STATE_OFF, command=self.update_plugin_frame).grid(row=current_row, column=1, padx=10, sticky=tk.W); current_row += 1 # LANG: Preferences checkbox label
        current_row += 1
        
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=15, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Commander API Settings", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        cmdrs: list = self.Comguard.CmdrManager.cmdrs
        if [] == cmdrs:
            cmdrs = [""]
        self.display_cmdr(self.Comguard.CmdrManager.get_cmdr_name())

        #Add callback and stuff
        nb.OptionMenu(frame, self.fieldCmdr, cmdrs[0], *cmdrs, command=self.select_cmdr).grid(row=current_row, column=1, padx=10, pady=1, sticky=tk.W)
        current_row += 1
        nb.Label(frame, text="Comguard.app account (Required)").grid(row=current_row, column=0, padx=x_pad, pady=1, sticky=tk.W)
        HyperlinkLabel(frame, text='Login / Sign up', background=nb.Label().cget('background'), url='https://comguard.app/profile.php', underline=True).grid(row=current_row, column=1, padx=x_pad, sticky=tk.W)  # Don't translate
        current_row += 1
        nb.Label(frame, text="Comguard API Key").grid(row=current_row, column=0, padx=x_pad, pady=1, sticky=tk.W)
        nb.EntryMenu(frame, textvariable=self.fieldAPIKey, width=64).grid(row=current_row, column=1, padx=x_button_pad, pady=y_pad, sticky=tk.W)
        nb.Button(frame, text="Apply", command=self.apply_api).grid(sticky=tk.E, row=current_row, column=1, padx=x_pad, pady=1)
        current_row += 1
        nb.Label(frame, text="API Status").grid(row=current_row, column=0, padx=x_pad, pady=y_pad, sticky=tk.W)
        nb.Label(frame, textvariable=self.APITestStatus).grid(row=current_row, column=1, padx=x_pad, pady=y_pad, sticky=tk.W)
        current_row += 1
        nb.Button(frame, textvariable=self.labelApiConnect, command=self.activate_api).grid(sticky=tk.W, row=current_row, column=1, padx=x_pad, pady=1)
        current_row += 1

        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=current_row, columnspan=2, padx=10, pady=15, sticky=tk.EW); current_row += 1
        nb.Label(frame, text="Danger Zone", font=FONT_HEADING_2).grid(row=current_row, column=0, padx=10, sticky=tk.W) # LANG: Preferences label
        nb.Button(frame, text="Reset Comguard Plugin", command=self.Comguard.zeroize).grid(sticky=tk.W, row=current_row, column=1, padx=x_pad, pady=1)
        current_row += 1
        nb.Label(frame, text="Warning, this will wipe all data, API Keys and detected commanders").grid(row=current_row, column=1, padx=x_pad, pady=y_pad, sticky=tk.W)

        return frame

    def select_cmdr(self, event=None):
        self.display_cmdr(self.fieldCmdr.get())

    def display_cmdr(self, cmdrName:str):
        apiKey: str = self.Comguard.CmdrManager.get_api_key(cmdrName)
        apiActive: bool = self.Comguard.CmdrManager.get_api_active(cmdrName)
        Debug.logger.debug(f"Choosing CMDR {cmdrName}, API Key is {apiKey}, API active = {apiActive}")
        
        self.fieldCmdr.set(cmdrName)
        self.fieldAPIKey.set(apiKey)
        if False == apiActive:
            self.APITestStatus.set(LBL_API_OFF)
            self.labelApiConnect.set(LBL_CONNECT)
        else:
            self.APITestStatus.set(LBL_API_ON)
            self.labelApiConnect.set(LBL_DISCONNECT)


    def display_data(self, dataTable):
        form = tk.Toplevel(self.frame)
        form.title(f"{self.Comguard.plugin_name} v{str(self.Comguard.version)}")
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


    def apply_api(self):
        cmdrName:str = self.fieldCmdr.get()
        apiKey: str = self.fieldAPIKey.get()
        self.Comguard.CmdrManager.set_api(cmdrName, apiKey)
        self.display_cmdr(cmdrName)


    def activate_api(self):
        self.apply_api()
        cmdrName:str = self.fieldCmdr.get()
        apiKey: str = self.Comguard.CmdrManager.get_api_key(cmdrName)
        apiActive: bool = self.Comguard.CmdrManager.get_api_active(cmdrName)
        Debug.logger.info(f"Changing API for {cmdrName} with API Key {apiKey}, API active = {apiActive}")
        if False == apiActive:
            #CONNECT API
            self.APITestStatus.set("Connecting . . .")
            activation: tuple = self.Comguard.Api.test_api(apiKey)
            self.Comguard.CmdrManager.set_api_active(cmdrName, activation[0])
            self.display_cmdr(cmdrName)
            self.APITestStatus.set(activation[1])
        else:
            #DISCONNECT API
            self.Comguard.CmdrManager.set_api_active(cmdrName, False)
            self.display_cmdr(cmdrName)


    def display_tick(self, ticktime):
        self.TimeLabel.set(tick_format(ticktime))


#SAVE CONFIG
    def save_prefs(self, cmdr):
        """
        Save settings
        """
        self.Comguard.save_data()
        self.StatusLabel["text"] = self.Comguard.Status.get()

        self.update_plugin_frame()


    def update_plugin_frame(self):
        """
        Update the UI if this function is necessary
        """
        self.StatusLabel.configure(text=self.Comguard.Status.get())

    def _worker(self) -> None:
        """
        Handle thread work for overlay
        """
        Debug.logger.debug("Starting UI Worker...")

        while True:
            if config.shutting_down:
                Debug.logger.debug("Shutting down UI Worker...")
                return

            sleep(TIME_WORKER_PERIOD_S)

