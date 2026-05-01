"""Module for Pocket Option Base websocket channel."""


class Base(object):
    """Base class for all Pocket Option websocket channel objects.
    
    Holds a reference to the API instance and delegates
    send_websocket_request to it.
    """

    def __init__(self, api):
        self.api = api

    def send_websocket_request(self, name, msg, request_id="", no_force_send=True):
        """Delegate websocket request to the API layer."""
        return self.api.send_websocket_request(name, msg, request_id, no_force_send)
