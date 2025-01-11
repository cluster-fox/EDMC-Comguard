import json
from queue import Queue
from re import match
from threading import Thread
from time import sleep

import semantic_version
import requests

from comguard.constants import RequestMethod
from comguard.debug import Debug
from comguard.requestmanager import RequestManager

API_VERSION = "1.7.0"
ENDPOINT_EVENTS = "https://comguard.app/api/events"

HEADER_APIKEY = "apikey"
HEADER_APIVERSION = "apiversion"
TIME_EVENTS_WORKER_PERIOD_S = 5
BATCH_EVENTS_MAX_SIZE = 10

class Api:
    """
    Connect and send messages to the API
    """

    def __init__(self, comguard):
        self.Comguard = comguard

        # Events queue is used to batch up events API messages. All batched messages are sent when the worker works.
        self.EventsQueue:Queue = Queue()

        self.EventsThread: Thread = Thread(target=self._events_worker, name=f"Comguard API Worker")
        self.EventsThread.daemon = True
        self.EventsThread.start()

    
    def trim_event(self, event):
        """
        Remove extra stuff from the events: everything Localized, Extra useless information, etc.
        """
        #jump events are a whitelist to trim most useless information
        jumpWhitelist = ['timestamp', 'event', 'StarSystem', 'SystemAddress', 'Population', 'Factions', 'Conflicts', 'SystemFaction']
        event.pop('Type_Localised', None)
        return event


    def send_data(self, cmdr, event: dict, systemAddress: int, systemName: str, stationFaction: str = ''):
        apiKey: str = self.Comguard.CmdrManager.get_api_key(cmdr)
        apiActive: bool = self.Comguard.CmdrManager.get_api_active(cmdr)
        if apiActive:
            apiheaders = {
                "apikey": apiKey,
                "apiversion" : API_VERSION
            }
            if 'StarSystem' not in event:
                event['StarSystem'] = systemName
            if 'SystemAddress' not in event:
                event['SystemAddress'] = systemAddress
            if (stationFaction != '') and ('StationFaction' not in event) and ('SystemFaction' not in event) and ('Faction' not in event) and ('FactionEffects' not in event) and ('Factions' not in event):
                event['StationFaction'] = {
                    "Name": stationFaction
                }
            payload = [event]
            Debug.logger.info(json.dumps(payload))
            try:
                response = requests.post(
                    url=ENDPOINT_EVENTS,
                    headers=apiheaders,
                    json=payload,
                    timeout=5
                )
            except requests.exceptions.Timeout:
                Debug.logger.warning('Comguard API timed out')
            else:
                Debug.logger.info(response)


    def test_api(self, apiKey:str) -> tuple[bool, str]:
        codes: dict[int, tuple] = {
            200: (True, "API Activated"),
            400: (False, "Error: Unknown Error occured"),
            401: (False, "Error: Invalid API Key"),
            404: (False, "Error: Could not connect to Comguard"),
            408: (False, "Error: Request timed out")
        }
        apiheaders = {
            "apikey": apiKey,
            "apiversion" : API_VERSION
        }
        payload = [{
                "timestamp" : "2022-01-01T00:00:00Z",
                "event" : "API test",
                "cmdr" : "",
                "StarSystem" : "Tau-3 Gruis",
                "SystemAddress" : 61440246972
            }]
        Debug.logger.info(json.dumps(payload))
        try:
            response = requests.post(
                url=ENDPOINT_EVENTS,
                headers=apiheaders,
                json=payload,
                timeout=5
            )
        except requests.exceptions.Timeout:
            return codes[408]
        else:
            return codes.get(response.status_code, codes[400])


    def _events_worker(self) -> None:
        """
        Handle events API. If there's queued events, this worker triggers a call to the events endpoint
        on a regular time period, sending the currently queued batch of events.
        """
        Debug.logger.debug("Starting Events API Worker...")

        while True:
            if self.EventsQueue.qsize() > 0:
                url:str = ENDPOINT_EVENTS

                # Grab all available events in the queue up to a maximum batch size
                batch_size:int = BATCH_EVENTS_MAX_SIZE
                queued_events:list = [self.EventsQueue.get(block=False) for _ in range(min(batch_size, self.EventsQueue.qsize()))]
                self.Comguard.RequestManager.queue_request(url, RequestMethod.POST, headers=self._get_headers(), payload=queued_events)

            sleep(TIME_EVENTS_WORKER_PERIOD_S)

