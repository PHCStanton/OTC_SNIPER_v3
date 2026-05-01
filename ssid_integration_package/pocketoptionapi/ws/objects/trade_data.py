import logging
import json
from datetime import datetime, timedelta  # добавляем timedelta
import pocketoptionapi.global_value as global_value

logger = logging.getLogger(__name__)


class TradeData:
    """
    Trade data handler for PocketOption API

    This class provides methods for:
    - Processing trade messages
    - Tracking open/closed trades
    - Calculating trading statistics

    Usage:
        # Get trading statistics
        stats = api.websocket_client.trade_handler.get_statistics()

        # Get trade history
        trades = api.websocket_client.trade_handler.get_trade_history()

        # Get open trades
        open_trades = api.websocket_client.trade_handler.get_open_trades()
    """
    """Class for handling trade data and statistics"""

    def __init__(self):
        self.trades = {}  # История всех сделок
        self.open_trades = {}  # Активные сделки
        self.statistics = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_profit': 0,
            'win_rate': 0,
        }

    def process_trade_message(self, message):
        """
        Process incoming trade message

        Args:
            message (dict or list): Trade message from websocket
        """
        try:
            # Проверяем, является ли сообщение списком истории сделок
            if isinstance(message, list) and len(message) > 0:
                # Проверяем структуру сообщения на соответствие истории сделок
                if all(isinstance(item, dict) and 'id' in item and 'openTime' in item for item in message):
                    logger.debug(f"Received trade history with {len(message)} trades")
                    # Обрабатываем каждую сделку
                    for trade in message:
                        trade_id = trade['id']
                        self.trades[trade_id] = {
                            'id': trade_id,
                            'openTime': trade.get('openTime'),
                            'closeTime': trade.get('closeTime'),
                            'asset': trade.get('asset'),
                            'amount': trade.get('amount'),
                            'profit': trade.get('profit'),
                            'percentProfit': trade.get('percentProfit'),
                            'openPrice': trade.get('openPrice'),
                            'closePrice': trade.get('closePrice'),
                            'direction': trade.get('command'),
                            'isDemo': trade.get('isDemo'),
                            'currency': trade.get('currency'),
                            'status': 'win' if trade.get('profit', 0) > 0 else 'loss'
                        }
                        # Обновляем статистику
                        self.update_statistics(self.trades[trade_id])
                    return

            # Обработка нового ордера
            if isinstance(message, dict):
                if "requestId" in message and message["requestId"] == 'buy':
                    self.handle_new_order(message)

                # Обработка закрытой сделки
                elif "deals" in message:
                    self.handle_closed_deal(message)

                # Обновление баланса и профита
                self.update_financial_data(message)

        except Exception as e:
            logger.error(f"Error processing trade message: {e}")

    def handle_new_order(self, message):
        """Process new order data"""
        try:
            order_id = message.get("id")
            if order_id:
                self.open_trades[order_id] = {
                    'id': order_id,
                    'openTime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'asset': message.get('asset'),
                    'amount': message.get('amount'),
                    'direction': message.get('action'),
                    'openPrice': message.get('current_price'),
                    'isDemo': message.get('isDemo', 1)
                }

                # Обновляем глобальные переменные
                global_value.order_data = message
                global_value.order_open.append(order_id)

                logger.debug(f"New order opened: {order_id}")

        except Exception as e:
            logger.error(f"Error handling new order: {e}")

    def handle_closed_deal(self, message):
        """Process closed deal data"""
        try:
            if "deals" in message and message["deals"]:
                deal = message["deals"][0]
                deal_id = deal["id"]

                # Собираем полные данные о сделке
                trade_data = {
                    'id': deal_id,
                    'openTime': deal.get('openTime'),
                    'closeTime': deal.get('closeTime'),
                    'asset': deal.get('asset'),
                    'amount': deal.get('amount'),
                    'profit': deal.get('profit'),
                    'percentProfit': deal.get('percentProfit'),
                    'openPrice': deal.get('openPrice'),
                    'closePrice': deal.get('closePrice'),
                    'direction': deal.get('command'),
                    'isDemo': deal.get('isDemo'),
                    'currency': deal.get('currency'),
                    'status': 'win' if deal.get('profit', 0) > 0 else 'loss'
                }

                # Сохраняем данные
                self.trades[deal_id] = trade_data

                # Обновляем статистику
                self.update_statistics(trade_data)

                # Обновляем глобальные переменные
                global_value.order_closed.append(deal_id)
                global_value.stat.append([deal_id, trade_data['status']])

                # Удаляем из открытых сделок
                if deal_id in self.open_trades:
                    del self.open_trades[deal_id]

                logger.debug(f"Deal closed: {deal_id}, Profit: {trade_data['profit']}")

        except Exception as e:
            logger.error(f"Error handling closed deal: {e}")

    def update_financial_data(self, message):
        """Update financial indicators"""
        if "profit" in message:
            global_value.profit = message["profit"]
        if "percentProfit" in message:
            global_value.percent_profit = message["percentProfit"]
        if "current_price" in message:
            global_value.current_price = message["current_price"]
        if "volume" in message:
            global_value.volume = message["volume"]
        if "balance" in message:
            global_value.balance = message["balance"]

    def update_statistics(self, trade_data):
        """Update trading statistics"""
        self.statistics['total_trades'] += 1

        if trade_data['status'] == 'win':
            self.statistics['wins'] += 1
        else:
            self.statistics['losses'] += 1

        self.statistics['total_profit'] += trade_data['profit']
        self.statistics['win_rate'] = (self.statistics['wins'] / self.statistics['total_trades']) * 100

    def get_trade_history(self):
        """Get complete trade history"""
        return self.trades

    def get_open_trades(self):
        """Get currently open trades"""
        return self.open_trades

    def get_statistics(self):
        """Get current trading statistics"""
        return self.statistics

    def get_filtered_history(self, asset=None, start_date=None, end_date=None, is_demo=None, min_amount=None):
        """Get filtered trade history"""
        try:
            filtered_trades = []

            for trade_id, trade in self.trades.items():
                if asset and trade['asset'] != asset:
                    continue

                if start_date:
                    trade_time = datetime.strptime(trade['openTime'], "%Y-%m-%d %H:%M:%S")
                    if trade_time < datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S"):
                        continue

                if end_date:
                    trade_time = datetime.strptime(trade['openTime'], "%Y-%m-%d %H:%M:%S")
                    if trade_time > datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S"):
                        continue

                if is_demo is not None and trade['isDemo'] != is_demo:
                    continue

                if min_amount and trade['amount'] < min_amount:
                    continue

                filtered_trades.append(trade)

            return filtered_trades

        except Exception as e:
            logger.error(f"Error filtering trade history: {e}")
            return []

    def get_trade_details(self, trade_id):
        """Get detailed information about specific trade"""
        try:
            if trade_id in self.trades:
                trade = self.trades[trade_id]

                # Добавляем дополнительные расчеты
                duration = (datetime.strptime(trade['closeTime'], "%Y-%m-%d %H:%M:%S") -
                            datetime.strptime(trade['openTime'], "%Y-%m-%d %H:%M:%S")).total_seconds()

                price_change = trade['closePrice'] - trade['openPrice']
                price_change_percent = (price_change / trade['openPrice']) * 100

                return {
                    **trade,  # Исходные данные сделки
                    'duration_seconds': duration,
                    'price_change': price_change,
                    'price_change_percent': price_change_percent,
                    'direction_str': 'CALL' if trade['direction'] == 0 else 'PUT'
                }

            return None

        except Exception as e:
            logger.error(f"Error getting trade details: {e}")
            return None

    def get_statistics_by_period(self, period_start, period_end):
        """Get trading statistics for specific period"""
        try:
            filtered_trades = self.get_filtered_history(start_date=period_start, end_date=period_end)

            stats = {
                'total_trades': len(filtered_trades),
                'wins': 0,
                'losses': 0,
                'total_profit': 0,
                'win_rate': 0,
                'average_profit': 0,
                'best_trade': None,
                'worst_trade': None
            }

            for trade in filtered_trades:
                if trade['status'] == 'win':
                    stats['wins'] += 1
                else:
                    stats['losses'] += 1

                stats['total_profit'] += trade['profit']

                # Отслеживаем лучшую/худшую сделки
                if not stats['best_trade'] or trade['profit'] > stats['best_trade']['profit']:
                    stats['best_trade'] = trade
                if not stats['worst_trade'] or trade['profit'] < stats['worst_trade']['profit']:
                    stats['worst_trade'] = trade

            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
                stats['average_profit'] = stats['total_profit'] / stats['total_trades']

            return stats

        except Exception as e:
            logger.error(f"Error calculating period statistics: {e}")
            return None