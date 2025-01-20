# EDMC-Comguard
An EDMC plugin to record BGS work and send the data to Comguard

Fully supports multiple-commanders and alternate accounts

This plugin requires an account on [Comguard](https://comguard.app)

# Installation
Requires [Elite Dangerous Market Connector](https://github.com/EDCD/EDMarketConnector/releases/latest) (EDMC)

1. Install EDMC

2. Download the [latest release](https://github.com/cluster-fox/EDMC-Comguard/releases/latest) of EDMC-Comguard

3. From EDMC, go to the Settings menu

4. Under the Plugins Tab press the “Open” button. 
>This will show the plugins folder for EDMC

5. Extract the EDMC-Comguard .zip archive that you downloaded inside the plugins folder.

6. Close and restart EDMC to reload with the new plugin.

# Setup
1. Create an account on [Comguard](https://comguard.app)
> you will need your squadron's invite key to proceed

2. From your [Comguard profile](https://comguard.app/profile), you will see a 32 character, alphanumeric API KEY

3. Copy the API Key

4. From EDMC, go to the Settings menu

5. Under the EDMC-Comguard Tab, paste the API Key.

6. Click Apply, then Click Activate API

7. The status will change from Disconnected to Connected

# Usage
EDMC-Comguard automatically records the BGS work you do for any faction, in any system and sends it to your squadron via the Comguard.app API.

It is highly recommended to have EDMC running before Elite is launched as your CMDR's location is initialized at startup. Not doing this can result in missing or erroneous data.

The data is shown on a pop up window when the Data Today button on the EDMC main screen is pushed.

The plugin can be paused in the EDMC-Comguard Tab under EDMC Settings.

Each CMDR's API can be connected or disconnected individually.

From v3.0+ we log the following activities:
- Conflict zones

From v2.2 we count the following activities. 
- Mission inf +
- Total trade profit sold to Faction controlled station
- Cartographic data sold to Faction controlled station
- Bounties issued by named Faction.
- Combat Bonds issued by named Faction
- Missions Failed for named Faction
- Ships murdered owned by named Faction
- Missions are counted when a Faction is in Election. Only missions that my research suggests work during Election are counted, this is a work in progress
- Negative trade is counted with a minus sign in trade profit column.

These total during the session and reset at server tick.
The state column has 3 options, None, War or Election to give an indication on how missions are being counted

# Credits

Orginally Forked from Tez's (tezw21) BGS-Tally 

Version 3.0+ is largely adapted from Aussi's own fork of BGS-Tally and shares the same API.

API design by Cluster Fox and Aussi
