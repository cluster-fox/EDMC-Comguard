# EDMC-Comguard
An EDMC plugin to record BGS work and send the data to Comguard

Forked from Tez's (tezw21) BGS-Tally and adapated to uplink the data to [Comguard](https://comguard.app)

# Installation
Download the [latest release](https://github.com/cluster-fox/EDMC-Comguard/releases/latest) of EDMC-Comguard
 - In EDMC, open Settings
 - On the Plugins Tab (Rightmost) press the “Open” button. This reveals the plugins folder where this app looks for plugins.
 - Open the .zip archive that you downloaded and extract as a subfolder contained inside the plugins folder.

You will need to re-start EDMC for it to notice the new plugin.

# Usage
EDMC-Comguard records the BGS work you do for any faction, in any system and sends it to your squadron via the Comguard.app API. 
It is highly recommended that EDMC is started before ED is launched as Data is recorded at startup and then when you dock at a station. Not doing this can result in missing data.
The data is shown on a pop up window when the Data Today button on the EDMC main screen is pushed.
The plugin can be paused in the EDMC-Comguard Tab under EDMC Settings.

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
