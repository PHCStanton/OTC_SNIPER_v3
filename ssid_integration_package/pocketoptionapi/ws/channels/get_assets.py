# pocketoptionapi/ws/channels/get_assets.py

from pocketoptionapi.ws.channels.base import Base
from pocketoptionapi.ws.objects.asset import AssetManager  # Добавляем этот импорт
import pocketoptionapi.global_value as global_value
import logging

logger = logging.getLogger(__name__)


class GetAssets(Base):
    name = "updateAssets"
    _instance = None  # Добавляем для синглтона

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, api):
        if not hasattr(self, '_initialized'):
            super().__init__(api)
            self.asset_manager = AssetManager()
            self._initialized = True
            logger.debug("GetAssets initialized with new AssetManager")

    def __call__(self):
        """Send request to get available assets"""
        data = ["updateAssets", {"placeholder": "true", "num": 0}]
        logger.debug("Sending assets request")
        return self.send_websocket_request(self.name, data)

    def process_assets_response(self, data):
        """Process received assets data"""
        try:
            logger.debug(f"Processing assets response. Data length: {len(data)}")
            self.asset_manager.process_assets(data)
            # Сохраняем тот же экземпляр в global_value
            global_value.asset_manager = self.asset_manager
            logger.debug(f"Assets processed. Total: {len(self.asset_manager.assets)}")
        except Exception as e:
            logger.error(f"Error processing assets: {e}")
            raise