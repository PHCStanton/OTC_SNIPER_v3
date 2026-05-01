# python
websocket_is_connected = False
# try fix ssl.SSLEOFError: EOF occurred in violation of protocol (_ssl.c:2361)
ssl_Mutual_exclusion = False  # mutex read write
# if false websocket can sent self.websocket.send(data)
# else can not sent self.websocket.send(data)
ssl_Mutual_exclusion_write = False  # if thread write

SSID = None

check_websocket_if_error = False
websocket_error_reason = None

balance_id = None
balance = None
balance_type = None
balance_updated = None
result = None
order_data = {}
order_open = []
order_closed = []
stat = []
DEMO = None

# Новые переменные для хранения значений
profit = None
percent_profit = None
current_price = None
volume = None
available_assets = None
asset_manager = None

def reset_trading_state():
    """Reset trading-related state only (for account switching)"""
    global balance, balance_id, balance_type, balance_updated
    global result, order_data, order_open, order_closed, stat
    global profit, percent_profit, current_price, volume
    global available_assets, asset_manager
    
    balance_id = None
    balance = None
    balance_type = None
    balance_updated = None
    result = None
    order_data = {}
    order_open = []
    order_closed = []
    stat = []
    profit = None
    percent_profit = None
    current_price = None
    volume = None
    available_assets = None
    asset_manager = None


def reset_all():
    """Reset ALL global state (for full disconnect)"""
    global websocket_is_connected, ssl_Mutual_exclusion, ssl_Mutual_exclusion_write
    global SSID, DEMO
    global check_websocket_if_error, websocket_error_reason
    
    reset_trading_state()
    
    websocket_is_connected = False
    ssl_Mutual_exclusion = False
    ssl_Mutual_exclusion_write = False
    SSID = None
    DEMO = None
    check_websocket_if_error = False
    websocket_error_reason = None
