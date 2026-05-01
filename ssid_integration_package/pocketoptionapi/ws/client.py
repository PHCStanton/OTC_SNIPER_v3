import asyncio
from datetime import datetime, timedelta, timezone
import websockets
import json
import logging
import ssl
import pocketoptionapi.constants as OP_code
import pocketoptionapi.global_value as global_value
from pocketoptionapi.constants import REGION
from pocketoptionapi.ws.objects.time_sync import TimeSync
from pocketoptionapi.ws.objects.trade_data import TradeData
from collections import defaultdict

logger = logging.getLogger(__name__)

time_sync = TimeSync()


async def on_open():
    """Method to process websocket open."""
    print("CONNECTED SUCCESSFUL")
    logger.debug("Websocket client connected.")
    global_value.websocket_is_connected = True


async def send_ping(ws):
    while global_value.websocket_is_connected is False:
        await asyncio.sleep(0.1)
    while True:
        await asyncio.sleep(20)
        await ws.send('42["ps"]')


class WebsocketClient(object):
    def __init__(self, api) -> None:
        self.updateHistoryNew = None
        self.updateStream = None
        self.history_data_ready = None
        self.successCloseOrder = False
        self.api = api
        self.message = None
        self.url = None
        self.ssid = global_value.SSID
        self.websocket = None
        self.region = REGION()
        self.loop = asyncio.get_event_loop()
        self.wait_second_message = False
        self._updateClosedDeals = False
        self.trade_handler = TradeData()
        self.available_assets = None

    async def websocket_listener(self, ws):
        try:
            async for message in ws:
                await self.on_message(message)
        except Exception as e:
            logging.warning(f"Error occurred: {e}")
            await self.close()

    async def close(self):
        """Method to properly close the websocket connection."""
        try:
            # Send closing message if connection is active
            if self.websocket and not self.websocket.closed:
                await self.websocket.send("42[\"leave\"]")

            # Set connection flag to False
            global_value.websocket_is_connected = False

            # Close WebSocket connection
            if self.websocket:
                await self.websocket.close()

            # Clear data
            self.websocket = None
            self.url = None
            self._updateClosedDeals = False
            self.wait_second_message = False
            self.updateHistoryNew = None
            self.updateStream = None
            self.history_data_ready = None
            self.successCloseOrder = False
            self.available_assets = None

            logger.info("WebSocket connection closed successfully")

        except Exception as e:
            logger.error(f"Error while closing connection: {e}")

    async def connect(self):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            await self.close()
        except:
            pass

        while not global_value.websocket_is_connected:
            # For DEMO: use dedicated demo server
            if global_value.DEMO:
                urls = ["wss://demo-api-eu.po.market/socket.io/?EIO=4&transport=websocket"]
            else:
                # For REAL: use region rotation
                urls = self.region.get_regions(True)

            for url in urls:
                print(url)
                try:
                    async with websockets.connect(
                            url,
                            ssl=ssl_context,
                            extra_headers={"Origin": "https://pocketoption.com", "Cache-Control": "no-cache"},
                            user_agent_header="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ) as ws:
                        self.websocket = ws
                        self.url = url
                        global_value.websocket_is_connected = True

                        # Create and execute tasks
                        on_message_task = asyncio.create_task(self.websocket_listener(ws))
                        sender_task = asyncio.create_task(self.send_message(self.message))
                        ping_task = asyncio.create_task(send_ping(ws))

                        await asyncio.gather(on_message_task, sender_task, ping_task)

                except websockets.ConnectionClosed as e:
                    global_value.websocket_is_connected = False
                    await self.on_close(e)
                    logger.warning("Trying another server")

                except Exception as e:
                    global_value.websocket_is_connected = False
                    await self.on_error(e)

            await asyncio.sleep(1)

        return True

    async def send_message(self, message):
        while global_value.websocket_is_connected is False:
            await asyncio.sleep(0.1)

        self.message = message

        if global_value.websocket_is_connected and message is not None:
            try:
                await self.websocket.send(message)
            except Exception as e:
                logger.warning(f"Error sending message: {e}")
                await self.close()
        elif message is not None:
            logger.warning("WebSocket not connected")

    @staticmethod
    def dict_queue_add(self, dict, maxdict, key1, key2, key3, value):
        if key3 in dict[key1][key2]:
            dict[key1][key2][key3] = value
        else:
            while True:
                try:
                    dic_size = len(dict[key1][key2])
                except:
                    dic_size = 0
                if dic_size < maxdict:
                    dict[key1][key2][key3] = value
                    break
                else:
                    del dict[key1][key2][sorted(dict[key1][key2].keys(), reverse=False)[0]]

    async def on_message(self, message):
        logger.debug(message)

        if type(message) is bytes:
            message = message.decode('utf-8')
            try:
                message = json.loads(message)

                # Проверяем, является ли сообщение массивом активов
                if isinstance(message, list) and len(message) > 0:
                    if all(isinstance(x, list) and len(x) >= 14 for x in message):
                        try:
                            if hasattr(self.api, 'get_assets'):
                                self.api.get_assets.process_assets_response(message)
                                logger.debug(f"Processed {len(message)} assets")
                            return
                        except Exception as e:
                            logger.error(f"Error processing assets: {e}")

                # Handle trade data
                self.trade_handler.process_trade_message(message)

                # Balance updates
                if "balance" in message:
                    if "uid" in message:
                        global_value.balance_id = message["uid"]
                    global_value.balance = message["balance"]
                    global_value.balance_type = message["isDemo"]

                # Order updates
                elif "requestId" in message and message["requestId"] == 'buy':
                    global_value.order_data = message
                    global_value.order_open.append(message["id"])

                # Deal updates
                elif "deals" in message:
                    if message["profit"] > 0:
                        stat = "win"
                    else:
                        stat = "loss"
                    ido = message["deals"][0]["id"]
                    pack = [ido, stat]
                    global_value.order_closed.append(ido)
                    global_value.stat.append(pack)

                # Symbol updates
                if "changeSymbol" in str(message):
                    if "quotation" in message:
                        global_value.current_price = message.get("quotation", {}).get("bid")
                        global_value.volume = message.get("quotation", {}).get("volume")
                        global_value.percent_profit = message.get("profit_percent")

                # Profit updates
                if "profit" in message:
                    global_value.profit = message["profit"]

                if "percentProfit" in message:
                    global_value.percent_profit = message["percentProfit"]

                elif self.wait_second_message and isinstance(message, list):
                    self.wait_second_message = False
                    self._updateClosedDeals = False

                elif isinstance(message, dict) and self.successCloseOrder:
                    self.api.order_async = message
                    self.successCloseOrder = False

                elif self.history_data_ready and isinstance(message, dict):
                    self.history_data_ready = False
                    self.api.history_data = message["data"]

                elif self.updateStream and isinstance(message, list):
                    self.updateStream = False
                    self.api.time_sync.server_timestamp = message[0][1]

                elif self.updateHistoryNew and isinstance(message, dict):
                    self.updateHistoryNew = False
                    self.api.historyNew = message

                return

            except json.JSONDecodeError:
                logger.warning(f"Failed to decode message: {message}")
                return

        if message.startswith('0') and "sid" in message:
            await self.websocket.send("40")

        elif message == "2":
            await self.websocket.send("3")

        elif message.startswith("40") and "sid" in message:
            await self.websocket.send(global_value.SSID)

        elif message.startswith('451-['):
            try:
                json_part = message.split("-", 1)[1]
                message = json.loads(json_part)

                if message[0] == "successauth":
                    await on_open()

                elif message[0] == "successupdateBalance":
                    global_value.balance_updated = True

                elif message[0] == "successopenOrder":
                    global_value.result = True

                elif message[0] == "updateClosedDeals":
                    self._updateClosedDeals = True
                    self.wait_second_message = True
                    await self.websocket.send('42["changeSymbol",{"asset":"AUDNZD_otc","period":60}]')

                elif message[0] == "successcloseOrder":
                    self.successCloseOrder = True
                    self.wait_second_message = True

                elif message[0] == "loadHistoryPeriod":
                    self.history_data_ready = True

                elif message[0] == "updateStream":
                    self.updateStream = True

                elif message[0] == "updateHistoryNew":
                    self.updateHistoryNew = True

                elif message[0] == "updateAssets":
                    logger.debug("Received updateAssets notification")
                    if len(message) > 1 and isinstance(message[1], list):
                        if hasattr(self.api, 'get_assets'):
                            self.api.get_assets.process_assets_response(message[1])
                            logger.debug(f"Assets processed via 451: {len(message[1])} assets")

            except (IndexError, json.JSONDecodeError) as e:
                logger.error(f"Failed to parse message: {e}")
                return

        elif message.startswith("42") and "NotAuthorized" in message:
            logging.error("User not Authorized: Please Change SSID for one valid")
            global_value.ssl_Mutual_exclusion = False
            await self.close()

    async def on_error(self, error):
        logger.error(error)
        global_value.websocket_error_reason = str(error)
        global_value.check_websocket_if_error = True
        await self.close()

    async def on_close(self, error):
        logger.warning(f"WebSocket connection closed. Reason: {error}")
        global_value.websocket_is_connected = False
        await self.close()




