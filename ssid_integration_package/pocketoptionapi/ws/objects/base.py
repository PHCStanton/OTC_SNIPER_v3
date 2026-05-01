"""Module for Pocket Option Base websocket object."""


class Base(object):
    """Base class for all Pocket Option websocket objects."""

    def __init__(self):
        self.__name = None

    @property
    def name(self):
        """Property to get object name."""
        return self.__name

    @name.setter
    def name(self, name):
        """Method to set object name."""
        self.__name = name
