import datetime
import pandas as pd # Added import
from typing import List, Dict, Any, Optional # Added import
from src.core.models import Candle
from src.strategies.base_strategy import BaseStrategy
from src.data_handler.historical_data_manager import HistoricalDataManager
from src.analytics.performance_reporter import PerformanceReporter # Added import

# Placeholder for actual strategy

class BacktesterEngine:
    def __init__(self,
                 strategy: BaseStrategy,
                 broker,
                 historical_data_manager: HistoricalDataManager,
                 symbols: list[str],
                 timeframe: str,
                 start_date: datetime.datetime,
                 end_date: datetime.datetime,
                 generate_analytics_report: bool = True): # Added parameter
        
        self.strategy = strategy
        self.broker = broker
        self.historical_data_manager = historical_data_manager
        self.symbols_to_trade = symbols
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.generate_analytics_report = generate_analytics_report # Store parameter
        
        self.equity_curve: List[float] = []
        self.portfolio_history: List[Dict[str, Any]] = []

    def _convert_trades_to_dataframe(self, trade_objects: list) -> pd.DataFrame:
        """
        Converts a list of trade objects/dictionaries into a Pandas DataFrame.
        """
        if not trade_objects:
            return pd.DataFrame()

        df = pd.DataFrame(trade_objects)
        
        # Ensure essential columns are present, others can be optional
        required_cols = ['symbol', 'side', 'quantity', 'price', 'timestamp', 'pnl']
        for col in required_cols:
            if col not in df.columns:
                self.broker.logger.warning(f"Trade history is missing required column: {col}. Performance report trade metrics might be inaccurate.")
                # Add missing column with NaNs or default values if appropriate
                df[col] = None 
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Convert numeric columns
        numeric_cols = ['quantity', 'price', 'pnl', 'commission']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce') # Coerce errors to NaN

        # Ensure pnl exists, as it's critical for PerformanceReporter
        if 'pnl' not in df.columns:
             self.broker.logger.error("Critical 'pnl' column missing in trade history. Trade-based metrics will be unavailable.")
             # Create a dummy pnl column if it's absolutely necessary and makes sense,
             # otherwise PerformanceReporter should handle its absence.
             # For now, we rely on PerformanceReporter to handle missing 'pnl'.

        return df

    def run(self):
        # 1. Fetch and prepare data
        all_market_data = self.historical_data_manager.get_all_data_sorted_by_timestamp(
            symbols=self.symbols_to_trade,
            timeframe=self.timeframe,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        if not all_market_data:
            self.broker.logger.warning("No market data fetched for the given symbols and date range.")
            # Return empty results, or whatever is appropriate
            return [], []


        # 2. Main backtesting loop
        for current_timestamp, bars_for_timestamp in all_market_data:

            self.broker.current_time = current_timestamp

            active_bars_for_this_timestamp = {}
            for symbol in self.symbols_to_trade:
                bar = bars_for_timestamp.get(symbol)
                if bar:
                    self.broker.set_current_bar(symbol, bar)
                    active_bars_for_this_timestamp[symbol] = bar
            
            if not active_bars_for_this_timestamp:
                pass 

            if active_bars_for_this_timestamp: 
                self.broker._process_pending_orders()

            if active_bars_for_this_timestamp: 
                self.strategy.on_bar(active_bars_for_this_timestamp)

            balance_info = self.broker.get_balance()
            positions = self.broker.get_positions() 

            current_portfolio_value = balance_info['cash']
            current_positions_market_value = 0.0
            detailed_positions = {}

            for pos_data in positions: 
                pos_symbol = pos_data.get('symbol')
                pos_qty = pos_data.get('quantity', 0)
                pos_avg_price = pos_data.get('average_price', 0.0)
                
                if pos_qty == 0: 
                    detailed_positions[pos_symbol] = {"qty": 0, "avg_price": 0.0, "last_price": pos_data.get('last_price', 0.0), "market_value": 0.0}
                    continue

                current_pos_bar = self.broker.get_current_bar(pos_symbol)
                market_value_of_position = 0
                last_price_for_pos = pos_data.get('last_price', 0.0) 

                if current_pos_bar and hasattr(current_pos_bar, 'close'):
                    last_price_for_pos = current_pos_bar.close
                    market_value_of_position = pos_qty * current_pos_bar.close
                else:
                    market_value_of_position = pos_qty * last_price_for_pos
                
                current_positions_market_value += market_value_of_position
                detailed_positions[pos_symbol] = {"qty": pos_qty, "avg_price": pos_avg_price, "last_price": last_price_for_pos, "market_value": market_value_of_position}

            current_portfolio_value += current_positions_market_value
            
            # self.equity_curve.append(current_portfolio_value) # Original line, seems to store only values
            self.portfolio_history.append({
                "timestamp": current_timestamp,
                "cash": balance_info['cash'],
                "positions_market_value": current_positions_market_value,
                "total_value": current_portfolio_value,
                "positions": detailed_positions # Storing detailed positions can be heavy if not needed for equity curve
            })
            
        self.broker.logger.info("Backtest run completed.")

        # 3. Generate Analytics Report (if enabled)
        if self.generate_analytics_report:
            self.broker.logger.info("Generating analytics report...")
            trade_log = self.broker.get_trade_history()
            trade_df = self._convert_trades_to_dataframe(trade_log)

            if not self.portfolio_history:
                self.broker.logger.warning("Portfolio history is empty. Cannot generate analytics report.")
                # Return original equity_curve (values only) and portfolio_history
                return [entry['total_value'] for entry in self.portfolio_history], self.portfolio_history


            timestamps = [entry['timestamp'] for entry in self.portfolio_history]
            values = [entry['total_value'] for entry in self.portfolio_history]
            
            temp_df = pd.DataFrame({'timestamp': pd.to_datetime(timestamps), 'value': values})
            if temp_df.empty: # check after creation from potentially empty history
                 self.broker.logger.warning("Portfolio history resulted in an empty DataFrame. Cannot generate analytics report.")
                 return [entry['total_value'] for entry in self.portfolio_history], self.portfolio_history


            if temp_df['timestamp'].duplicated().any():
                self.broker.logger.warning("Duplicate timestamps found in portfolio history. Using last value for each timestamp.")
                # Sort by timestamp first to ensure 'last' is chronologically last if duplicates are not ordered
                temp_df = temp_df.sort_values('timestamp').groupby('timestamp').last()
            else:
                # Set index even if no duplicates, for consistency with the duplicated case
                temp_df = temp_df.set_index('timestamp').sort_index()

            equity_curve_series = pd.Series(temp_df['value'], name="Equity") # Index is already set
            
            if equity_curve_series.empty:
                self.broker.logger.warning("Equity curve is empty after processing. Cannot generate analytics report.")
            else:
                # Instantiate PerformanceReporter
                # Assuming benchmark_returns is None for now. This can be enhanced later.
                reporter = PerformanceReporter(trades=trade_df, equity_curve=equity_curve_series, benchmark_returns=None)
                
                # Generate unique filenames
                strategy_name = self.strategy.__class__.__name__
                current_time_str = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
                
                report_path = f"backtest_report_{strategy_name}_{current_time_str}.html"
                plot_output_path = f"equity_curve_{strategy_name}_{current_time_str}.png"

                # Generate report and plot
                try:
                    reporter.generate_quantstats_report(output_path=report_path, title=f"Strategy Performance: {strategy_name}")
                    self.broker.logger.info(f"Generated QuantStats report: {report_path}")
                    
                    reporter.plot_equity_curve(show=False, output_path=plot_output_path)
                    self.broker.logger.info(f"Generated Equity Curve plot: {plot_output_path}")
                except Exception as e:
                    self.broker.logger.error(f"Error during analytics report generation: {e}")

        # Return the original format of equity_curve (list of values) and portfolio_history
        return [entry['total_value'] for entry in self.portfolio_history], self.portfolio_history


if __name__ == '__main__': # pragma: no cover
    # Example Usage (Conceptual - requires concrete Strategy, Broker, DataManager)
    
    # from src.broker_api.mock_fyers_client import MockFyersClient
    # from src.core.models import Order, OrderType, OrderSide 
    
    # # 1. Mock Broker
    # mock_broker = MockFyersClient(logger=None) # Provide a logger if available
    # mock_broker.connect()

    # # 2. Historical Data Manager (Conceptual)
    # class MyHistoricalDataManager(HistoricalDataManager):
    #     def __init__(self, data):
    #         self._data = data # data is pre-loaded list of (timestamp, {symbol: Candle})
            
    #     def get_all_data_sorted_by_timestamp(self, symbols, timeframe, start_date, end_date):
    #         # Filter data by date range if necessary, here just returning all
    #         return self._data
    
    # # Dummy data for two timestamps, one symbol 'SBIN'
    # candle1_time = datetime.datetime(2023,1,1,9,15)
    # candle2_time = datetime.datetime(2023,1,1,9,16)
    # candle1 = Candle(timestamp=candle1_time, symbol="SBIN", open=100,high=102,low=99,close=101,volume=1000)
    # candle2 = Candle(timestamp=candle2_time, symbol="SBIN", open=101,high=103,low=100,close=102,volume=1200)
    # market_data_feed = [
    #     (candle1.timestamp, {"SBIN": candle1}),
    #     (candle2.timestamp, {"SBIN": candle2})
    # ]
    # data_manager = MyHistoricalDataManager(data=market_data_feed)

    # # 3. Strategy (Conceptual)
    # class MyStrategy(BaseStrategy):
    #     def __init__(self, symbols_to_trade, broker_interface): # Added broker_interface
    #         self.symbols = symbols_to_trade
    #         self.invested = {}
    #         self.broker = broker_interface # Store broker for placing orders

    #     def on_bar(self, current_bar_data: dict): # Removed broker_interface from here
    #         for symbol in self.symbols:
    #             if symbol in current_bar_data:
    #                 bar = current_bar_data[symbol]
    #                 if not self.invested.get(symbol):
    #                     order = Order(symbol=symbol, quantity=1, side=OrderSide.BUY, order_type=OrderType.MARKET)
    #                     # self.broker is now part of the strategy instance
    #                     trade_result = self.broker.place_order(order) 
    #                     if trade_result and trade_result.get('status') == 'filled':
    #                         print(f"{bar.timestamp}: Placed BUY order for {symbol} at {trade_result.get('fill_price', bar.close)}")
    #                         self.invested[symbol] = True
    
    # strategy_symbols = ["SBIN"]
    # # Pass broker to strategy constructor if it needs it for placing orders
    # my_strategy = MyStrategy(strategy_symbols, broker_interface=mock_broker) 


    # # 4. Engine
    # engine = BacktesterEngine(
    #     strategy=my_strategy,
    #     broker=mock_broker,
    #     historical_data_manager=data_manager,
    #     symbols=strategy_symbols,
    #     timeframe="1minute",
    #     start_date=datetime.datetime(2023,1,1),
    #     end_date=datetime.datetime(2023,1,2),
    #     generate_analytics_report=True # Enable report generation
    # )
    # raw_equity_curve, portfolio_history = engine.run()
    
    # print("\nRaw Equity Curve (values only):", raw_equity_curve)
    # if portfolio_history:
    #     print(f"\nPortfolio History (last entry): {portfolio_history[-1]}")
    # else:
    #     print("\nPortfolio History is empty.")

    # print("\nTrade Log from Broker:")
    # for trade in mock_broker.get_trade_history():
    #     print(trade)
    pass
