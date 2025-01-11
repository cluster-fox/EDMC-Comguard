class CmdrLocation:
    """
    This is a conveninence container more than anything
    """
    def __init__(self, cmdrData):
        self.CmdrData = cmdrData

        self.system: int = 0
        self.conflicts: list = []
        self.faction: str = ""
        self.fleetCarrier: bool = False
        self.settlement: dict = {}
        self.conflictZone: dict = {}
        self.megaship: dict = {}

    def set_conflicts(self, conflictData):
        self.conflicts = []
        for conflict in conflictData:
            if conflict['Status'] != "active": 
                continue

            faction_1:str = conflict['Faction1']['Name']
            faction_2:str = conflict['Faction2']['Name']

            self.conflicts.append([faction_1, faction_2])

    def get_opponent(self, factionName:str) -> str:
        for conflict in self.conflicts:
            if conflict[0] == factionName:
                return conflict[1]
            elif conflict[1] == factionName:
                return conflict[0]
        return ''
    