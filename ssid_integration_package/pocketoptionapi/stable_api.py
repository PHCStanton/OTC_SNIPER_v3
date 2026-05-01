import asyncio
import threading
import time
import logging
import pandas as pd
import json
import pocketoptionapi.global_value as global_value
import pocketoptionapi.constants as OP_code
from tzlocal import get_localzone
from pocketoptionapi.api import PocketOptionAPI
from collections import defaultdict
from collections import deque
from typing import List, Optional, Any


# Получение локальной временной зоны
local_zone_name = get_localzone()


def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))


def get_balance():
    return global_value.balance


class PocketOption:
    __version__ = "1.0.0"

    def __init__(self, ssid):
        """Initialize Pocket Option API

        Args:
            ssid (str): SSID string for authentication
        """
        self.size = [1, 5, 10, 15, 30, 60, 120, 180, 300, 600, 900, 1800,
                     3600, 7200, 14400, 28800, 43200, 86400, 604800, 2592000]

        # Note: global_value.SSID and global_value.DEMO are now managed 
        # by PocketOptionSession to ensure consistency.
        is_demo = global_value.DEMO

        self.suspend = 0.5
        self.thread = None
        self.subscribe_candle = []
        self.subscribe_candle_all_size = []
        self.subscribe_mood = []
        self.get_digital_spot_profit_after_sale_data = nested_dict(2, int)
        self.get_realtime_strike_list_temp_data = {}
        self.get_realtime_strike_list_temp_expiration = 0
        self.SESSION_HEADER = {
            "User-Agent": r"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          r"Chrome/66.0.3359.139 Safari/537.36"}
        self.SESSION_COOKIE = {}

        # Инициализируем API с определенным режимом
        self.api = PocketOptionAPI(ssid)
        self.loop = asyncio.get_event_loop()

        logger = logging.getLogger(__name__)
        logger.info(f"Initializing {'Demo' if is_demo else 'Real'} account connection")

    def get_server_timestamp(self):
        return self.api.time_sync.server_timestamp

    def get_server_datetime(self):
        return self.api.time_sync.server_datetime

    def set_session(self, header, cookie):
        self.SESSION_HEADER = header
        self.SESSION_COOKIE = cookie

    def get_async_order(self, buy_order_id):
        if self.api.order_async["deals"][0]["id"] == buy_order_id:
            return self.api.order_async["deals"][0]
        else:
            return None

    def get_async_order_id(self, buy_order_id):
        return self.api.order_async["deals"][0][buy_order_id]

    def start_async(self):
        asyncio.run(self.api.connect())

    def connect(self):
        """
        Синхронный метод для установки соединения.
        Использует внутренний цикл событий asyncio для выполнения coroutine подключения.
        """
        try:
            self.thread = threading.Thread(target=self.api.connect, daemon=True)
            self.thread.start()
        except Exception as e:
            print(f"Error connecting: {e}")
            return False
        return True

    def disconnect(self):
        """Stop the websocket connection and clean up the thread."""
        try:
            global_value.websocket_is_connected = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=3)
        except Exception as e:
            logging.warning(f"Disconnect error: {e}")

    @staticmethod
    def check_connect():
        if global_value.websocket_is_connected == 0:
            return False
        elif global_value.websocket_is_connected is None:
            return False
        else:
            return True

    @staticmethod
    def get_balance():
        if global_value.balance_updated:
            return global_value.balance
        else:
            return None

    @staticmethod
    def check_open():
        return global_value.order_open

    @staticmethod
    def check_order_closed(ido):
        while ido not in global_value.order_closed:
            time.sleep(0.1)

        for pack in global_value.stat:
            if pack[0] == ido:
                print('Order Closed', pack[1])
        return pack[0]

    def buy(self, amount, active, action, expirations):
        self.api.buy_multi_option = {}
        self.api.buy_successful = None
        req_id = "buy"

        try:
            if req_id not in self.api.buy_multi_option:
                self.api.buy_multi_option[req_id] = {"id": None}
            else:
                self.api.buy_multi_option[req_id]["id"] = None
        except Exception as e:
            logging.error(f"Error initializing buy_multi_option: {e}")
            return False, None

        global_value.order_data = None
        global_value.result = None

        self.api.buyv3(amount, active, action, expirations, req_id)

        start_t = time.time()
        while True:
            if global_value.result is not None and global_value.order_data is not None:
                break
            if time.time() - start_t >= 5:
                if isinstance(global_value.order_data, dict) and "error" in global_value.order_data:
                    logging.error(global_value.order_data["error"])
                else:
                    logging.error("Unknown error occurred during buy operation")
                return False, None
            time.sleep(0.1)

        return global_value.result, global_value.order_data.get("id", None)

    def check_win(self, id_number):
        start_t = time.time()
        order_info = None

        while True:
            try:
                order_info = self.get_async_order(id_number)
                if order_info and "id" in order_info and order_info["id"] is not None:
                    break
            except:
                pass

            if time.time() - start_t >= 120:
                logging.error("Timeout: Could not retrieve order info in time.")
                return None, "unknown"

            time.sleep(0.1)

        if order_info and "profit" in order_info:
            status = "win" if order_info["profit"] > 0 else "lose"
            return order_info["profit"], status
        else:
            logging.error("Invalid order info retrieved.")
            return None, "unknown"

    def buy_advanced(self, amount, active, action, expirations, on_new_candle=False):
        """Advanced buy method with new candle mode support

        Args:
            amount: Trade amount
            active: Asset symbol
            action: Trade direction
            expirations: Option expiration time
            on_new_candle: If True, wait for new candle
        """
        try:
            self.api.buy_multi_option = {}
            self.api.buy_successful = None
            req_id = "buy"

            # Инициализация опций
            if req_id not in self.api.buy_multi_option:
                self.api.buy_multi_option[req_id] = {"id": None}
            else:
                self.api.buy_multi_option[req_id]["id"] = None

            # Сброс глобальных значений
            global_value.order_data = None
            global_value.result = None

            # Используем расширенный метод покупки без параметра timeframe
            self.api.buy_advanced(
                amount=amount,
                active=active,
                direction=action,
                duration=expirations,
                request_id=req_id,
                on_new_candle=on_new_candle
            )

            # Ждем результат
            start_t = time.time()
            while True:
                if global_value.result is not None and global_value.order_data is not None:
                    break
                if time.time() - start_t >= 5:
                    if isinstance(global_value.order_data, dict) and "error" in global_value.order_data:
                        logging.error(global_value.order_data["error"])
                    else:
                        logging.error("Unknown error occurred during buy operation")
                    return False, None
                time.sleep(0.1)

            return global_value.result, global_value.order_data.get("id", None)

        except Exception as e:
            logging.error(f"Error in buy_advanced: {e}")
            return False, None

    @staticmethod
    def last_time(timestamp, period):
        timestamp_rounded = (timestamp // period) * period
        return int(timestamp_rounded)

    def get_candles(self, active, timeframe, count):
        """Get historical candles

        Args:
            active: Asset symbol (e.g. "EURUSD_otc")
            timeframe: Timeframe in seconds
            count: Number of candles

        Returns:
            List of candles in format [[time, open, high, low, close], ...]
        """
        try:
            candles = self.api.get_candles_data(active, timeframe, count)
            if not candles:
                return []

            formatted_candles = [
                [
                    candle['time'],
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close']
                ]
                for candle in candles
            ]

            if self.check_data(formatted_candles, timeframe):
                return formatted_candles
            return []

        except Exception as e:
            logger.error(f"Error in get_candles: {e}")
            return []

    def check_data(self, candles, timeframe):
        """Check candles data integrity"""
        try:
            if not candles:
                return False

            for i in range(len(candles) - 1):
                current = candles[i]
                next_candle = candles[i + 1]

                time_diff = next_candle[0] - current[0]
                if time_diff != timeframe:
                    logger.error(f"Invalid time interval: {time_diff}")
                    return False

                if current[2] < current[3]:
                    logger.error(f"High less than Low at {datetime.fromtimestamp(current[0])}")
                    return False

                if (current[1] > current[2] or
                        current[1] < current[3] or
                        current[4] > current[2] or
                        current[4] < current[3]):
                    logger.error(f"Invalid OHLC values at {datetime.fromtimestamp(current[0])}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking candles: {e}")
            return False


    @staticmethod
    def process_data_history(data, period):
        df = pd.DataFrame(data['history'], columns=['timestamp', 'price'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        df['minute_rounded'] = df['datetime'].dt.floor(f'{period / 60}min')

        ohlcv = df.groupby('minute_rounded').agg(
            open=('price', 'first'),
            high=('price', 'max'),
            low=('price', 'min'),
            close=('price', 'last')
        ).reset_index()

        ohlcv['time'] = ohlcv['minute_rounded'].apply(lambda x: int(x.timestamp()))
        ohlcv = ohlcv.drop(columns='minute_rounded')
        ohlcv = ohlcv.iloc[:-1]
        ohlcv_dict = ohlcv.to_dict(orient='records')

        return ohlcv_dict

    @staticmethod
    def process_candle(candle_data, period):
        data_df = pd.DataFrame(candle_data)
        data_df.sort_values(by='time', ascending=True, inplace=True)
        data_df.drop_duplicates(subset='time', keep="first", inplace=True)
        data_df.reset_index(drop=True, inplace=True)
        data_df.ffill(inplace=True)
        diferencias = data_df['time'].diff()
        diff = (diferencias[1:] == period).all()
        return data_df, diff

    def change_symbol(self, active, period):
        return self.api.change_symbol(active, period)

    def sync_datetime(self):
        return self.api.synced_datetime

    def check_assets_info(self):
        """
        Get detailed information about all assets and their availability
        Returns dict with statistics or None if assets are not available
        """
        try:
            if not self.check_connect():
                logging.error("Not connected to API")
                return None

            # Ждем получения активов
            timeout = 10
            start_time = time.time()
            while time.time() - start_time < timeout:
                if (hasattr(self.api, 'get_assets') and
                        hasattr(self.api.get_assets, 'asset_manager') and
                        self.api.get_assets.asset_manager.assets):
                    return self.api.get_assets.asset_manager.analyze_by_category()
                time.sleep(0.1)

            logging.error("Timeout waiting for assets")
            return None

        except Exception as e:
            logging.error(f"Error checking assets: {e}")
            return None

    def print_assets_info(self):
        """Print detailed information about all assets and their availability"""
        stats = self.check_assets_info()
        if not stats:
            print("Unable to get assets information")
            return

        print("\n=== АКТИВЫ ПО КАТЕГОРИЯМ ===")
        total_assets = 0
        total_available = 0
        total_unavailable = 0

        for category, data in sorted(stats.items()):
            print(f"\n{category.upper()}")
            print("=" * (len(category) + 2))
            print(f"Всего активов: {data['total']}")
            print(f"Доступных: {data['available']}")
            print(f"Недоступных: {data['unavailable']}")

            # Получаем все активы этой категории
            category_assets = self.api.get_assets.asset_manager.get_assets_by_type(category)

            # Разделяем на доступные и недоступные
            available = [asset for asset in category_assets if asset.is_available]
            unavailable = [asset for asset in category_assets if not asset.is_available]

            print("\nДоступные активы:")
            if available:
                for asset in sorted(available, key=lambda x: x.name):
                    print(f"  - {asset.name} ({asset.symbol})")
            else:
                print("  Нет доступных активов")

            print("\nНедоступные активы:")
            if unavailable:
                for asset in sorted(unavailable, key=lambda x: x.name):
                    print(f"  - {asset.name} ({asset.symbol})")
            else:
                print("  Нет недоступных активов")

            print("-" * 50)

            total_assets += data['total']
            total_available += data['available']
            total_unavailable += data['unavailable']

        print("\n=== ОБЩАЯ СТАТИСТИКА ===")
        print(f"Всего активов: {total_assets}")
        print(f"Доступных активов: {total_available}")
        print(f"Недоступных активов: {total_unavailable}")
        print(f"Процент доступных: {(total_available / total_assets * 100):.1f}%")
        print("=" * 50)

    def get_assets(self):
        """
        Get list of all available assets
        Returns:
            list: List of Asset objects
        """
        try:
            if not global_value.asset_manager:
                self.api.get_assets()
                start_time = time.time()
                while not global_value.asset_manager and time.time() - start_time < 10:
                    time.sleep(0.1)

            if global_value.asset_manager:
                return global_value.asset_manager.get_all_assets()
            return []
        except Exception as e:
            logging.error(f"Error getting assets: {e}")
            return []

    def get_available_assets(self):
        """
        Get list of assets available for trading
        Returns:
            list: List of available Asset objects
        """
        try:
            assets = self.get_assets()
            return [asset for asset in assets if asset.is_trading_allowed]
        except Exception as e:
            logging.error(f"Error getting available assets: {e}")
            return []

    def get_asset_by_symbol(self, symbol: str):
        """
        Get asset by its symbol
        Args:
            symbol (str): Asset symbol (e.g. 'EURUSD')
        Returns:
            Asset or None: Asset object if found, None otherwise
        """
        try:
            if global_value.asset_manager:
                return global_value.asset_manager.get_asset_by_symbol(symbol)
            return None
        except Exception as e:
            logging.error(f"Error getting asset by symbol: {e}")
            return None

    def get_profitable_assets(self, min_profit: float = None):
        """
        Get list of assets sorted by profit
        Args:
            min_profit (float): Minimum profit percentage
        Returns:
            list: List of Asset objects sorted by profit
        """
        try:
            if global_value.asset_manager:
                return global_value.asset_manager.get_profitable_assets(min_profit)
            return []
        except Exception as e:
            logging.error(f"Error getting profitable assets: {e}")
            return []