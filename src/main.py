import datetime
import logging

# Assuming project structure src/data, src/core, etc.
from src.data.historical_data_manager import HistoricalDataManager
from src.broker_api.mock_fyers_client import MockFyersClient
from src.strategies.example_moving_average_cross_strategy import ExampleMovingAverageCrossStrategy
from src.backtester.engine import BacktesterEngine
from src.core.models import Candle, Timeframe # OrderSide, OrderType are used within strategy/broker

# Basic Logging Configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Ensure logs go to console
    ]
)

if __name__ == "__main__":
    logger = logging.getLogger(__name__) # Logger for main execution

    # a. Setup Parameters
    symbol = "SBIN_NSE"
    start_date = datetime.datetime(2023, 1, 1)
    end_date = datetime.datetime(2023, 1, 31) # Using a 31-day period
    # Timeframe for data generation and strategy (ensure consistency)
    data_timeframe = Timeframe.DAY_1 
    initial_cash = 100000.0
    commission_rate_broker = 0.0007 # Example commission

    logger.info(f"Setting up backtest for {symbol} from {start_date.date()} to {end_date.date()} with {data_timeframe.value} timeframe.")

    # b. Prepare Historical Data (Sample Daily Data)
    sample_candles: list[Candle] = []
    current_date = start_date
    days_generated = 0
    base_open = 100.0
    while current_date <= end_date and days_generated < 31: # Generate up to 31 candles or until end_date
        # Simple price movement for MA crossover
        open_price = base_open + days_generated * 0.5
        close_price = base_open + days_generated * 0.5 - (days_generated % 5) + 2 # Creates some up/down for MA
        if days_generated > 10 and days_generated < 20 : # dip
             close_price = base_open + days_generated * 0.5 - (days_generated % 3) - 5
        if days_generated > 20 : # recovery
            close_price = base_open + days_generated * 0.5 + (days_generated % 2) + 3


        sample_candles.append(Candle(
            timestamp=current_date,
            symbol=symbol,
            open=open_price,
            high=open_price + 2.0, # Simplified high
            low=open_price - 2.0,   # Simplified low
            close=close_price,
            volume=10000 + days_generated * 100,
            timeframe=data_timeframe 
        ))
        current_date += datetime.timedelta(days=1)
        days_generated +=1
    
    if not sample_candles:
        logger.error("No sample candles generated. Exiting.")
        exit()
        
    data_feeds = {symbol: sample_candles}
    logger.info(f"Generated {len(sample_candles)} sample candles for {symbol}.")

    # c. Instantiate Components
    hdm = HistoricalDataManager()
    hdm.load_data(data_feeds) # Load data into HDM
    
    # Pass HDM to broker if broker needs direct access to historical data (e.g. for fills)
    # MockFyersClient current implementation of place_order for MARKET uses its own historical_data if symbol not in current_bars
    # or get_current_bar.close(). It might be more robust to pass the HDM instance to the broker,
    # but current MockFyersClient historical_data is a dict or an object with get_data.
    # For simplicity, MockFyersClient was modified to accept historical_data, which can be an HDM.
    broker = MockFyersClient(
        historical_data=hdm, # Pass the HDM instance
        initial_cash=initial_cash, 
        commission_rate=commission_rate_broker
    )
    broker.connect() # Connect the broker

    strategy_config = {
        "symbol": symbol, 
        "short_window": 5, 
        "long_window": 10, 
        "quantity": 10,
        "timeframe": data_timeframe # Strategy might use this for context or internal logic
    }
    strategy = ExampleMovingAverageCrossStrategy(
        strategy_id="MA_Cross_1", 
        broker=broker, 
        config=strategy_config
    )
    
    # Engine uses timeframe for its own context if needed, but primarily relies on HDM's sorted data
    engine = BacktesterEngine(
        strategy=strategy, 
        broker=broker, 
        historical_data_manager=hdm, 
        symbols_to_trade=[symbol], 
        timeframe=data_timeframe.value, # Pass string value of timeframe
        start_date=start_date, 
        end_date=end_date
    )

    # d. Run Backtest
    logger.info("Starting backtest engine...")
    equity_curve, portfolio_history = engine.run()
    logger.info("Backtest engine finished.")

    # e. Print Results
    if equity_curve:
        logger.info(f"Final Portfolio Value: {equity_curve[-1]:.2f}")
    else:
        logger.info(f"Final Portfolio Value (no trades or activity): {initial_cash:.2f}")

    logger.info("Trade Log:")
    trade_log = broker.get_trade_history() # This returns a list of trade dicts
    if trade_log:
        for trade in trade_log:
            # Assuming trade is a dictionary as per MockFyersClient
            trade_info = (
                f"TradeID: {trade.get('trade_id')}, OrderID: {trade.get('order_id')}, Symbol: {trade.get('symbol')}, "
                f"Side: {trade.get('side')}, Qty: {trade.get('quantity')}, Price: {trade.get('price', 0.0):.2f}, "
                f"Comm: {trade.get('commission', 0.0):.2f}, TS: {trade.get('timestamp')}"
            )
            logger.info(f"  {trade_info}")
    else:
        logger.info("  No trades executed.")

    logger.info("Portfolio History Snapshots (last 5):")
    for snapshot in portfolio_history[-5:]:
        # Snapshot is a dictionary from BacktesterEngine
        snap_info = (
            f"TS: {snapshot.get('timestamp')}, Cash: {snapshot.get('cash', 0.0):.2f}, "
            f"PositionsVal: {snapshot.get('positions_market_value', 0.0):.2f}, TotalVal: {snapshot.get('total_value', 0.0):.2f}"
        )
        logger.info(f"  {snap_info}")
        for sym, pos_details in snapshot.get('positions', {}).items():
            logger.info(f"    {sym}: Qty={pos_details.get('qty')}, AvgP={pos_details.get('avg_price', 0.0):.2f}, LastP={pos_details.get('last_price', 0.0):.2f}, MktVal={pos_details.get('market_value', 0.0):.2f}")

    broker.disconnect() # Disconnect the broker
    logger.info("Main execution finished.")
