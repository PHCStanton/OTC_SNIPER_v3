"""Module for Pocket Option API."""
import asyncio
import datetime
import time
import json
import logging
import threading
import requests
import ssl
import atexit
import pocketoptionapi.global_value as global_value
from collections import deque, defaultdict
from pocketoptionapi.ws.client import WebsocketClient
from pocketoptionapi.ws.channels.get_balances import *
from pocketoptionapi.ws.channels.candles import GetCandles
from pocketoptionapi.ws.channels.buyv3 import *
from pocketoptionapi.ws.objects.time_sync import TimeSync
from pocketoptionapi.ws.objects.candle import CandleCollection
from pocketoptionapi.ws.channels.change_symbol import ChangeSymbol
from pocketoptionapi.ws.channels.get_assets import GetAssets
from pocketoptionapi.ws.channels.buy_advanced import BuyAdvanced

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))

class PocketOptionAPI(object):
    """Class for communication with Pocket Option API."""
    socket_option_opened = {}
    time_sync = TimeSync()
    candle_collection = CandleCollection()
    api_option_init_all_result = []
    api_option_init_all_result_v2 = []
    underlying_list_data = None
    position_changed = None
    instrument_quites_generated_data = nested_dict(2, dict)
    instrument_quotes_generated_raw_data = nested_dict(2, dict)
    instrument_quites_generated_timestamp = nested_dict(2, dict)
    strike_list = None
    leaderboard_deals_client = None
    order_async = None
    instruments = None
    financial_information = None
    buy_id = None
    buy_order_id = None
    traders_mood = {}
    order_data = None
    positions = None
    position = None
    deferred_orders = None
    position_history = None
    position_history_v2 = None
    available_leverages = None
    order_canceled = None
    close_position_data = None
    overnight_fee = None
    digital_option_placed_id = None
    live_deal_data = nested_dict(3, deque)
    subscribe_commission_changed_data = nested_dict(2, dict)
    real_time_candles = nested_dict(3, dict)
    real_time_candles_maxdict_table = nested_dict(2, dict)
    candle_generated_check = nested_dict(2, dict)
    candle_generated_all_size_check = nested_dict(1, dict)
    api_game_getoptions_result = None
    sold_options_respond = None
    tpsl_changed_respond = None
    auto_margin_call_changed_respond = None
    top_assets_updated_data = {}
    get_options_v2_data = None
    buy_multi_result = None
    buy_multi_option = {}
    result = None
    training_balance_reset_request = None
    balances_raw = None
    user_profile_client = None
    leaderboard_userinfo_deals_client = None
    users_availability = None
    history_data = None
    historyNew = None
    server_timestamp = None
    sync_datetime = None

    def __init__(self, ssid=None, proxies=None):
        """
        Initialize Pocket Option API

        Args:
            ssid (str): SSID string for authentication
            proxies (dict): (optional) The http request proxies
        """
        self.websocket_client = None
        self.websocket_thread = None
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.proxies = proxies
        self.buy_successful = None
        self.loop = asyncio.get_event_loop()

        # DEMO/SSID state is managed by PocketOptionSession before this is instantiated.
        # Read the already-validated values from global_value directly.
        if ssid:
            is_demo = global_value.DEMO  # Already set and validated by PocketOptionSession
            logger = logging.getLogger(__name__)
            logger.info(f"Initializing {'Demo' if is_demo else 'Real'} account connection")

        self.websocket_client = WebsocketClient(self)

    @property
    def websocket(self):
        """Property to get websocket."""
        return self.websocket_client

    def send_websocket_request(self, name, msg, request_id="", no_force_send=True):
        """Send websocket request to Pocket Option server."""
        logger = logging.getLogger(__name__)
        data = f'42{json.dumps(msg)}'

        while (global_value.ssl_Mutual_exclusion or global_value.ssl_Mutual_exclusion_write) and no_force_send:
            pass
        global_value.ssl_Mutual_exclusion_write = True

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.websocket.send_message(data))

        logger.debug(data)
        global_value.ssl_Mutual_exclusion_write = False

    def start_websocket(self):
        """Start websocket connection"""
        global_value.websocket_is_connected = False
        global_value.check_websocket_if_error = False
        global_value.websocket_error_reason = None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.websocket.connect())
        loop.run_forever()

        while True:
            try:
                if global_value.check_websocket_if_error:
                    return False, global_value.websocket_error_reason
                if global_value.websocket_is_connected is False:
                    return False, "Websocket connection closed."
                elif global_value.websocket_is_connected is True:
                    return True, None
            except:
                pass

    def connect(self):
        """Method for connection to Pocket Option API."""
        global_value.ssl_Mutual_exclusion = False
        global_value.ssl_Mutual_exclusion_write = False

        check_websocket, websocket_reason = self.start_websocket()

        if not check_websocket:
            return check_websocket, websocket_reason

        self.time_sync.server_timestamps = None
        while True:
            try:
                if self.time_sync.server_timestamps is not None:
                    break
            except:
                pass
        return True, None

    async def close(self, error=None):
        """Close websocket connection"""
        await self.websocket.on_close(error)
        self.websocket_thread.join()

    def websocket_alive(self):
        """Check if websocket is alive"""
        return self.websocket_thread.is_alive()

    @property
    def get_balances(self):
        """Property for get balances"""
        return Get_Balances(self)

    @property
    def buyv3(self):
        """Property for buyv3"""
        return Buyv3(self)

    @property
    def buy_advanced(self):
        """Property for advanced buy"""
        return BuyAdvanced(self)

    @property
    def getcandles(self):
        """Property for getcandles"""
        return GetCandles(self)

    @property
    def change_symbol(self):
        """Property for change_symbol"""
        return ChangeSymbol(self)

    @property
    def synced_datetime(self):
        """Get synced datetime"""
        try:
            if self.time_sync is not None:
                self.sync_datetime = self.time_sync.get_synced_datetime()
            else:
                logging.error("time_sync is not set")
                self.sync_datetime = None
        except Exception as e:
            logging.error(e)
            self.sync_datetime = None

        return self.sync_datetime

    @property
    def get_assets(self):
        """Property for get assets"""
        return GetAssets(self)

    @property
    def analyze_assets(self):
        """Property for analyzing assets state
        Returns dict with statistics by category if assets are loaded, None otherwise
        """
        try:
            if hasattr(self.get_assets, 'asset_manager'):
                return self.get_assets.asset_manager.analyze_by_category()
            return None
        except Exception as e:
            logging.error(f"Error analyzing assets: {e}")
            return None

    def get_candles_data(self, active: str, interval: int, count: int, end_time: int = None):
        """Get raw candles data from websocket

        Args:
            active (str): Asset identifier (e.g. "EURUSD_otc")
            interval (int): Timeframe in seconds
            count (int): Number of candles
            end_time (int, optional): End timestamp

        Returns:
            list: Raw candles data
        """
        try:
            if end_time is None:
                end_time = int(time.time())
                end_time = (end_time // interval) * interval

            # Очищаем предыдущие данные
            self.history_data = None

            # Проверяем корректность параметров
            if not isinstance(active, str):
                logger.error("Asset must be a string")
                return None

            if interval not in [60, 120, 180, 300, 600, 900, 1800, 3600, 7200, 14400, 28800, 86400]:
                logger.error("Invalid interval")
                return None

            if count < 1:
                logger.error("Count must be positive")
                return None

            # Запрашиваем свечи
            self.getcandles(active, interval, count, end_time)

            # Ждем получения данных с таймаутом
            timeout = 5
            start_t = time.time()
            while self.history_data is None:
                if time.time() - start_t > timeout:
                    logger.error("Timeout waiting for candles")
                    return None
                time.sleep(0.1)

            if self.history_data:
                # Сортируем по времени и возвращаем
                return sorted(self.history_data, key=lambda x: x['time'])

            return None

        except Exception as e:
            logger.error(f"Error getting candles data: {e}")
            return None