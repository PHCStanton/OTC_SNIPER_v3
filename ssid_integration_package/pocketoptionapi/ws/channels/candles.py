"""Module for Pocket option candles websocket chanel."""
import time
from pocketoptionapi.ws.channels.base import Base


class GetCandles(Base):
    """Class for Pocket option candles websocket chanel."""
    name = "sendMessage"

    def __call__(self, active_id: str, interval: int, count: int, end_time: int):
        """Method to send message to candles websocket chanel.

        Args:
            active_id: Asset identifier (e.g. "EURUSD_otc")
            interval: Candle duration in seconds (timeframe)
            count: Number of candles
            end_time: End timestamp
        """
        # Вычисляем offset для получения нужного количества свечей
        offset = count * interval

        data = {
            "asset": str(active_id),
            "index": end_time,
            "offset": offset,
            "period": interval,
            "time": end_time
        }

        msg = ["loadHistoryPeriod", data]
        self.send_websocket_request(self.name, msg)
