import random
from typing import Optional, Dict, List, TYPE_CHECKING, Any
# The following imports are primarily for the template string, not directly used by MockLLMInterface methods.
from src.strategies.base_strategy import BaseStrategy
from src.core.models import Order, OrderType, OrderSide, Candle
import logging # For the template
import random # For the template

# NOTE: EVOLVED_STRATEGY_TEMPLATE is a direct copy of DEFAULT_STRATEGY_TEMPLATE
# from evolutionary_engine.py. Consider refactoring to a shared constant to avoid duplication.
# Copied from DEFAULT_STRATEGY_TEMPLATE in evolutionary_engine.py
EVOLVED_STRATEGY_TEMPLATE = """
import logging
from src.strategies.base_strategy import BaseStrategy
from src.core.models import Order, OrderType, OrderSide, Candle
from typing import TYPE_CHECKING, Dict, List
import random

if TYPE_CHECKING:
    from src.broker_api.base_broker_client import BaseBrokerClient

class EvolvedStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, broker: 'BaseBrokerClient', config: dict = None):
        super().__init__(strategy_id, broker, config)
        
        self.symbol = self.config.get("symbol", "DEFAULT_SYMBOL")
        # --- PARAM START ---
        self.short_window = self.config.get("short_window", {{SHORT_WINDOW}})
        self.long_window = self.config.get("long_window", {{LONG_WINDOW}})
        self.quantity = self.config.get("quantity", {{QUANTITY}})
        # --- PARAM END ---
        
        self.prices: List[float] = []
        self.short_ma_values: List[float] = []
        self.long_ma_values: List[float] = []
        
        self.logger.info(
            "EvolvedStrategy '{}' initialized for {} ".format(self.strategy_id, self.symbol) + \
            "with short_window={}, long_window={}, quantity={}.".format(self.short_window, self.long_window, self.quantity)
        )

    def _calculate_sma(self, data: List[float], window: int) -> float | None:
        if len(data) < window:
            return None
        return sum(data[-window:]) / window

    def on_bar(self, current_bars: Dict[str, 'Candle']):
        current_bar = current_bars.get(self.symbol)
        
        if not current_bar:
            self.logger.debug("No current bar data for symbol {} at this timestamp.".format(self.symbol))
            return

        self.prices.append(current_bar.close)
        if len(self.prices) > self.long_window + 5: # Keep a reasonable buffer, trim older prices
            self.prices.pop(0)

        short_ma = self._calculate_sma(self.prices, self.short_window)
        long_ma = self._calculate_sma(self.prices, self.long_window)

        if short_ma is not None: self.short_ma_values.append(short_ma)
        if long_ma is not None: self.long_ma_values.append(long_ma)

        self.logger.debug("Symbol: {}, Close: {}, ShortMA: {}, LongMA: {}".format(self.symbol, current_bar.close, short_ma, long_ma))

        if short_ma is None or long_ma is None:
            self.logger.debug("Not enough data for MA calculation yet.")
            return

        all_positions = self.broker.get_positions()
        active_position = None
        for pos_dict in all_positions:
            if pos_dict.get('symbol') == self.symbol:
                active_position = pos_dict
                break
        
        if len(self.short_ma_values) < 2 or len(self.long_ma_values) < 2:
            return

        prev_short_ma = self.short_ma_values[-2]
        prev_long_ma = self.long_ma_values[-2]
        current_short_ma = short_ma
        current_long_ma = long_ma

        if current_short_ma > current_long_ma and prev_short_ma <= prev_long_ma:
            current_pos_qty = active_position.get('quantity', 0) if active_position else 0
            if current_pos_qty == 0:
                order = Order(id=None, symbol=self.symbol, quantity=self.quantity, side=OrderSide.BUY, order_type=OrderType.MARKET)
                try:
                    order_id, status = self.broker.place_order(order)
                    self.logger.info("BUY signal for {}. Placed MARKET order. ID: {}, Status: {}".format(self.symbol, order_id, status))
                except Exception as e:
                    self.logger.error("Error placing BUY order for {}: {}".format(self.symbol, e))
            else:
                self.logger.debug("BUY signal for {}, but already have position qty: {}. No action.".format(self.symbol, current_pos_qty))
        elif current_short_ma < current_long_ma and prev_short_ma >= prev_long_ma:
            current_pos_qty = active_position.get('quantity', 0) if active_position else 0
            if current_pos_qty > 0:
                order = Order(id=None, symbol=self.symbol, quantity=abs(current_pos_qty), side=OrderSide.SELL, order_type=OrderType.MARKET)
                try:
                    order_id, status = self.broker.place_order(order)
                    self.logger.info("SELL signal for {}. Placed MARKET order. ID: {}, Status: {}".format(self.symbol, order_id, status))
                except Exception as e:
                    self.logger.error("Error placing SELL order for {}: {}".format(self.symbol, e))
            else:
                self.logger.debug("SELL signal for {}, but no active long position. No action.".format(self.symbol))
"""

class MockLLMInterface:
    """
    A mock interface for simulating interactions with a Large Language Model (LLM).
    This class provides placeholder implementations for generating, mutating,
    and combining strategy code, without actual LLM calls.
    """
    def __init__(self, api_key: Optional[str] = "mock_api_key", model_name: str = "mock_model_v1"):
        """
        Initializes the MockLLMInterface.

        Args:
            api_key (Optional[str]): A mock API key (not used).
            model_name (str): A mock model name (not used).
        """
        self.api_key = api_key
        self.model_name = model_name
        # print(f"MockLLMInterface initialized with model: {self.model_name}")

    def generate_initial_strategy(self, prompt: str) -> str:
        """
        Generates a mock initial strategy code based on a prompt.
        Currently, it ignores the prompt and returns a predefined template.

        Args:
            prompt (str): The prompt to guide strategy generation.

        Returns:
            str: A mock Python strategy code string.
        """
        print(f"MockLLMInterface: generate_initial_strategy called with prompt: '{prompt[:50]}...'")
        
        short_window = random.randint(5, 20)
        long_window = random.randint(21, 50)
        quantity = random.randint(1, 10)

        # Ensure long_window is always greater than short_window
        if short_window >= long_window:
            long_window = short_window + random.randint(5, 15)

        # Replace placeholders in the template
        strategy_code = EVOLVED_STRATEGY_TEMPLATE.replace("{{SHORT_WINDOW}}", str(short_window))
        strategy_code = strategy_code.replace("{{LONG_WINDOW}}", str(long_window))
        strategy_code = strategy_code.replace("{{QUANTITY}}", str(quantity))

        return strategy_code

    def refine_strategy_code(self, code: str, feedback: str) -> str:
        """
        Simulates refining a strategy code based on feedback.
        Appends the feedback as a comment to the original code.

        Args:
            code (str): The strategy code string to be refined.
            feedback (str): Feedback to guide the refinement.

        Returns:
            str: The "refined" strategy code string.
        """
        print(f"MockLLMInterface: refine_strategy_code called with feedback: '{feedback[:100]}...'")
        return f"{code}\n# LLM Mock Refinement: Based on feedback - {feedback}"

    def combine_strategy_codes(self, code_a: str, code_b: str, prompt: str) -> str:
        """
        Simulates combining two strategy codes based on a prompt.
        Concatenates the two codes with a comment indicating the combination.

        Args:
            code_a (str): The first strategy code string.
            code_b (str): The second strategy code string.
            prompt (str): The prompt to guide the combination.

        Returns:
            str: The "combined" strategy code string.
        """
        print(f"MockLLMInterface: combine_strategy_codes called with prompt: '{prompt[:50]}...'")
        return f"{code_a}\n\n# --- Combined by MockLLMInterface based on: {prompt} ---\n\n{code_b}"

# Example Usage (for illustration and quick testing)
if __name__ == '__main__':
    llm = MockLLMInterface()

    print("\n--- Testing generate_initial_strategy ---")
    initial_code = llm.generate_initial_strategy("Create a simple moving average crossover strategy.")
    # print("Generated Initial Code (first 300 chars):")
    # print(initial_code[:300] + "...")
    assert EVOLVED_STRATEGY_TEMPLATE in initial_code 

    print("\n--- Testing refine_strategy_code ---")
    refined_code = llm.refine_strategy_code(initial_code, "The strategy seems too aggressive. Try to reduce risk.")
    # print("\nRefined Code (last 200 chars):")
    # print("..." + refined_code[-200:])
    assert "# LLM Mock Refinement: Based on feedback - The strategy seems too aggressive. Try to reduce risk." in refined_code

    print("\n--- Testing combine_strategy_codes ---")
    strategy_code_part1 = "class StrategyA: # part 1 details"
    strategy_code_part2 = "class StrategyB: # part 2 details"
    combined_code = llm.combine_strategy_codes(strategy_code_part1, strategy_code_part2, "Combine for diversification.")
    # print("\nCombined Code:")
    # print(combined_code)
    assert "# --- Combined by MockLLMInterface based on: Combine for diversification. ---" in combined_code
    assert strategy_code_part1 in combined_code
    assert strategy_code_part2 in combined_code
    
    print("\nMockLLMInterface tests completed.")
