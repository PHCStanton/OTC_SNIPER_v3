import datetime
import json
import time
import sys
from pocketoptionapi.ws.channels.base import Base
import logging
import pocketoptionapi.global_value as global_value

logger = logging.getLogger(__name__)


class BuyAdvanced(Base):
    """Advanced buy class with additional trading modes"""
    name = "sendMessage"

    def get_timeframe(self, active):
        """Get current timeframe for asset"""
        try:
            end_time = int(time.time())
            end_time = (end_time // 60) * 60  # округляем до минуты

            # Пробуем разные таймфреймы, начиная с минимального
            timeframes = [60, 120, 180, 300, 600, 900, 1800, 3600, 7200, 14400, 28800, 43200, 86400, 604800, 2592000]  # 1m, 5m, 15m, 30m, 1h

            for tf in timeframes:
                self.api.history_data = None
                self.api.getcandles(active, tf, 2, end_time)

                timeout = 5
                start_t = time.time()
                while self.api.history_data is None:
                    if time.time() - start_t > timeout:
                        continue
                    time.sleep(0.1)

                if len(self.api.history_data) >= 2:
                    detected_tf = self.api.history_data[1]['time'] - self.api.history_data[0]['time']
                    if detected_tf == tf:  # Если интервал совпадает с ожидаемым
                        logger.info(f"Detected active timeframe: {detected_tf} seconds")
                        return detected_tf

            logger.error("Could not detect active timeframe")
            return None

        except Exception as e:
            logger.error(f"Error getting timeframe: {e}")
            return None

    def wait_for_new_candle(self, timeframe: int) -> bool:
        """Wait for the start of a new candle

        Args:
            timeframe: Candle timeframe in seconds
        """
        try:
            current_time = int(time.time())
            seconds_until_next = timeframe - (current_time % timeframe)

            logger.info(f"Waiting {seconds_until_next} seconds for new candle")

            # Ожидание с индикацией
            while seconds_until_next > 0:
                sys.stdout.write(f"\rWaiting for new candle: {seconds_until_next} seconds  ")
                sys.stdout.flush()
                time.sleep(1)
                seconds_until_next -= 1
            print("\n")

            return True

        except KeyboardInterrupt:
            print("\nWaiting cancelled by user")
            return False
        except Exception as e:
            logger.error(f"Error waiting for new candle: {e}")
            return False

    def __call__(self, amount, active, direction, duration, request_id, on_new_candle=False):
        """
        Open new order with advanced options

        Args:
            amount: Trade amount
            active: Asset symbol
            direction: Trade direction
            duration: Option duration
            request_id: Request identifier
            on_new_candle: If True, wait for new candle
        """
        try:
            if on_new_candle:
                timeframe = self.get_timeframe(active)
                if timeframe is None:
                    logger.error("Could not determine timeframe")
                    return False

                if not self.wait_for_new_candle(timeframe):
                    logger.error("Failed to wait for new candle")
                    return False

            data_dict = {
                "asset": active,
                "amount": amount,
                "action": direction,
                "isDemo": 1 if global_value.DEMO else 0,
                "requestId": request_id,
                "optionType": 100,
                "time": duration
            }

            message = ["openOrder", data_dict]
            self.send_websocket_request(self.name, message, str(request_id))
            return True

        except Exception as e:
            logger.error(f"Error opening order: {e}")
            return False