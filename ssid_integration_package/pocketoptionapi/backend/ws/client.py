import websockets
import anyio
from rich.pretty import pprint as print
import json


class WebSocketClient:
    def __init__(self, session) -> None:
        self.SESSION = session
        self.handlers = {}  # Dictionary to store message handlers

    def add_handler(self, message_type, handler):
        """Add a custom message handler"""
        self.handlers[message_type] = handler

    async def websocket_client(self, url, message_processor):
        while True:
            try:
                async with websockets.connect(
                        url,
                        extra_headers={
                            "Origin": "https://po.trade/"
                        },
                ) as websocket:
                    print(f"Connected to {url}")
                    async for message in websocket:
                        await message_processor(message, websocket, url)
            except KeyboardInterrupt:
                print("Shutting down client...")
                return False
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed")
                await anyio.sleep(5)
            except Exception as e:
                print(f"Error: {str(e)}")
                print("Connection lost... reconnecting")
                await anyio.sleep(5)
        return True

    async def process_message(self, message, websocket, url):
        """Generic message processor that handles any incoming message"""

        # Handle binary messages
        if isinstance(message, bytes):
            print(f"Binary message received: {str(message[:100])}...")
            return

        print(f"Received message: {message}")

        # Handle basic protocol messages
        if message.startswith('0{"sid":"'):
            print(f"Initializing connection for {url}")
            await websocket.send("40")
        elif message == "2":  # Ping
            print(f"Ping received from {url}")
            await websocket.send("3")  # Pong
        elif message.startswith('40{"sid":"'):
            print(f"Authenticating connection for {url}")
            await websocket.send(self.SESSION)
            print("Authentication message sent")

        # Process message with custom handlers if registered
        try:
            message_data = json.loads(message) if message[0] in '[{' else message
            message_type = message_data.get('type') if isinstance(message_data, dict) else None

            if message_type and message_type in self.handlers:
                await self.handlers[message_type](message_data, websocket)
        except json.JSONDecodeError:
            # Not a JSON message, might be a protocol message
            pass
        except Exception as e:
            print(f"Error processing message: {str(e)}")

    async def main(self, urls=None):
        """
        Start the WebSocket client with one or multiple URLs

        Args:
            urls (str or list): Single URL or list of URLs to connect to
        """
        if urls is None:
            urls = ["wss://api-l.po.market/socket.io/?EIO=4&transport=websocket"]
        elif isinstance(urls, str):
            urls = [urls]

        tasks = []
        for url in urls:
            tasks.append(self.websocket_client(url, self.process_message))

        await anyio.gather(*tasks)


# Example usage:
async def example():
    client = WebSocketClient(session="your_session_token")

    # Add custom message handlers if needed
    async def handle_trade(message_data, websocket):
        print(f"Processing trade: {message_data}")

    client.add_handler('trade', handle_trade)

    # Start the client
    await client.main()


# Run the client
if __name__ == "__main__":
    anyio.run(example)
