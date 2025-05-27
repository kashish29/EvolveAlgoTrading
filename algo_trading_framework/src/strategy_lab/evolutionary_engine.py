import random
import re
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_STRATEGY_TEMPLATE = """
import logging
from algo_trading_framework.src.strategies.base_strategy import BaseStrategy
from algo_trading_framework.src.core.models import Order, OrderType, OrderSide, Candle
from typing import TYPE_CHECKING, Dict, List
import random

if TYPE_CHECKING:
    from algo_trading_framework.src.broker_api.base_broker_client import BaseBrokerClient

class EvolvedStrategy(BaseStrategy):
    def __init__(self, strategy_id: str, broker: 'BaseBrokerClient', config: dict = None):
        super().__init__(strategy_id, broker, config)
        
        self.symbol = self.config.get("symbol", "DEFAULT_SYMBOL")
        # --- PARAM START ---
        self.short_window = self.config.get("short_window", 5)
        self.long_window = self.config.get("long_window", 10)
        self.quantity = self.config.get("quantity", 1)
        # --- PARAM END ---
        
        self.prices: List[float] = []
        self.short_ma_values: List[float] = []
        self.long_ma_values: List[float] = []
        
        self.logger.info(
            f"EvolvedStrategy '{{self.strategy_id}}' initialized for {{self.symbol}} "
            f"with short_window={{self.short_window}}, long_window={{self.long_window}}, quantity={{self.quantity}}."
        )

    def _calculate_sma(self, data: List[float], window: int) -> float | None:
        if len(data) < window:
            return None
        return sum(data[-window:]) / window

    def on_bar(self, current_bars: Dict[str, 'Candle']):
        current_bar = current_bars.get(self.symbol)
        
        if not current_bar:
            self.logger.debug(f"No current bar data for symbol {{self.symbol}} at this timestamp.")
            return

        self.prices.append(current_bar.close)
        if len(self.prices) > self.long_window + 5: # Keep a reasonable buffer, trim older prices
            self.prices.pop(0)

        short_ma = self._calculate_sma(self.prices, self.short_window)
        long_ma = self._calculate_sma(self.prices, self.long_window)

        if short_ma is not None: self.short_ma_values.append(short_ma)
        if long_ma is not None: self.long_ma_values.append(long_ma)

        self.logger.debug(f"Symbol: {{self.symbol}}, Close: {{current_bar.close}}, ShortMA: {{short_ma}}, LongMA: {{long_ma}}")

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
                    self.logger.info(f"BUY signal for {{self.symbol}}. Placed MARKET order. ID: {{order_id}}, Status: {{status}}")
                except Exception as e:
                    self.logger.error(f"Error placing BUY order for {{self.symbol}}: {{e}}")
            else:
                self.logger.debug(f"BUY signal for {{self.symbol}}, but already have position qty: {{current_pos_qty}}. No action.")
        elif current_short_ma < current_long_ma and prev_short_ma >= prev_long_ma:
            current_pos_qty = active_position.get('quantity', 0) if active_position else 0
            if current_pos_qty > 0:
                order = Order(id=None, symbol=self.symbol, quantity=abs(current_pos_qty), side=OrderSide.SELL, order_type=OrderType.MARKET)
                try:
                    order_id, status = self.broker.place_order(order)
                    self.logger.info(f"SELL signal for {{self.symbol}}. Placed MARKET order. ID: {{order_id}}, Status: {{status}}")
                except Exception as e:
                    self.logger.error(f"Error placing SELL order for {{self.symbol}}: {{e}}")
            else:
                self.logger.debug(f"SELL signal for {{self.symbol}}, but no active long position. No action.")
"""

class EvolutionaryEngine:
    def __init__(self,
                 initial_strategy_template: str = DEFAULT_STRATEGY_TEMPLATE,
                 llm_interface: Optional[Any] = None, # Placeholder for future use
                 primary_fitness_metric: str = "sharpe_ratio",
                 tournament_size: int = 3,
                 elitism_count: int = 1,
                 mutation_probability: float = 0.1):
        self.initial_strategy_template = initial_strategy_template
        self.llm_interface = llm_interface # Currently unused
        self.primary_fitness_metric = primary_fitness_metric
        self.tournament_size = tournament_size
        self.elitism_count = elitism_count
        self.mutation_probability = mutation_probability
        self.param_ranges = {
            "short_window": (3, 20), # min_val, max_val
            "long_window": (10, 50),
            "quantity": (1, 10)
        }

    def _change_param_in_code(self, code_string: str, param_name: str, new_value: int) -> str:
        # Priority 1: self.param_name = self.config.get("param_name", DEFAULT_VALUE)
        pattern_config = re.compile(f'(self\.{param_name}\s*=\s*self\.config\.get\s*\(\s*"{param_name}"\s*,\s*)(\d+)(\s*\))')
        code_string, count_config = pattern_config.sub(rf'\g<1>{new_value}\g<3>', code_string, count=1)
        
        if count_config == 0:
            # Priority 2: self.param_name = VALUE
            pattern_direct = re.compile(f'(self\.{param_name}\s*=\s*)(\d+)')
            code_string, count_direct = pattern_direct.sub(rf'\g<1>{new_value}', code_string, count=1)
            if count_direct == 0:
                print(f"Warning: Param {param_name} not updated by _change_param_in_code in code snippet.")
        return code_string

    def _get_param_from_code(self, code_string: str, param_name: str) -> Optional[int]:
        # Priority 1: self.param_name = self.config.get("param_name", VALUE)
        match_config = re.search(f'self\.{param_name}\s*=\s*self\.config\.get\s*\(\s*"{param_name}"\s*,\s*(\d+)\s*\)', code_string)
        if match_config:
            return int(match_config.group(1))
        
        # Priority 2: self.param_name = VALUE
        match_direct = re.search(f'self\.{param_name}\s*=\s*(\d+)', code_string)
        if match_direct:
            return int(match_direct.group(1))
        
        # print(f"Warning: Param {param_name} not found by _get_param_from_code in code snippet.")
        return None

    def initialize_population(self, size: int) -> List[str]:
        population = []
        for _ in range(size):
            strategy_code = str(self.initial_strategy_template)
            
            # Adjust short_window first, ensuring it's low enough to allow a valid long_window
            new_sw = random.randint(*self.param_ranges["short_window"])
            if new_sw >= self.param_ranges["long_window"][1]: # Ensure sw can allow lw to be greater
                 new_sw = self.param_ranges["long_window"][1] - 1 
            new_sw = max(self.param_ranges["short_window"][0], new_sw) # Ensure sw is not below its own min

            strategy_code = self._change_param_in_code(strategy_code, "short_window", new_sw)

            # Adjust long_window
            min_lw = new_sw + 1
            max_lw = self.param_ranges["long_window"][1]
            if min_lw > max_lw : # Should not happen if new_sw was adjusted correctly
                min_lw = max_lw # Fallback, ensures randint doesn't fail
            
            new_lw = random.randint(min_lw, max_lw)
            strategy_code = self._change_param_in_code(strategy_code, "long_window", new_lw)

            # Adjust quantity
            new_qty = random.randint(*self.param_ranges["quantity"])
            strategy_code = self._change_param_in_code(strategy_code, "quantity", new_qty)
            
            population.append(strategy_code)
        return population

    def select_parents(self, population: List[str], fitness_scores: List[Dict[str, Any]]) -> List[str]:
        if not population or not fitness_scores or len(population) != len(fitness_scores):
            # Fallback: if inputs are problematic, return original population or empty list
            return population if population else []

        pop_with_fitness = list(zip(population, fitness_scores))
        parents = []
        
        for _ in range(len(population)):
            tournament_contenders = random.sample(pop_with_fitness, min(self.tournament_size, len(pop_with_fitness)))
            
            winner = tournament_contenders[0]
            max_fitness = winner[1].get(self.primary_fitness_metric, -float('inf'))
            if not isinstance(max_fitness, (int, float)): max_fitness = -float('inf')

            for i in range(1, len(tournament_contenders)):
                contender_fitness = tournament_contenders[i][1].get(self.primary_fitness_metric, -float('inf'))
                if not isinstance(contender_fitness, (int, float)): contender_fitness = -float('inf')
                if contender_fitness > max_fitness:
                    max_fitness = contender_fitness
                    winner = tournament_contenders[i]
            parents.append(winner[0])
        return parents

    def crossover(self, parent1_code: str, parent2_code: str) -> str:
        sw1 = self._get_param_from_code(parent1_code, "short_window")
        if sw1 is None: sw1 = random.randint(*self.param_ranges["short_window"])

        lw2 = self._get_param_from_code(parent2_code, "long_window")
        if lw2 is None: lw2 = random.randint(*self.param_ranges["long_window"])
        
        qty1 = self._get_param_from_code(parent1_code, "quantity")
        if qty1 is None: qty1 = random.randint(*self.param_ranges["quantity"])

        # Constraint Check for long_window vs short_window
        if lw2 <= sw1:
            min_lw_val = sw1 + 1
            max_lw_val = self.param_ranges["long_window"][1]
            if min_lw_val > max_lw_val: # sw1 is too high
                 sw1 = max_lw_val -1 # adjust sw1 down
                 sw1 = max(self.param_ranges["short_window"][0], sw1) # ensure sw1 respects its min
                 min_lw_val = sw1 + 1

            lw2 = random.randint(min_lw_val, max_lw_val)
            
        offspring_code = str(self.initial_strategy_template)
        offspring_code = self._change_param_in_code(offspring_code, "short_window", sw1)
        offspring_code = self._change_param_in_code(offspring_code, "long_window", lw2)
        offspring_code = self._change_param_in_code(offspring_code, "quantity", qty1)
        
        return offspring_code

    def mutate(self, strategy_code: str) -> str:
        code_copy = str(strategy_code)
        param_to_mutate = random.choice(list(self.param_ranges.keys()))
        
        new_val = random.randint(*self.param_ranges[param_to_mutate])

        if param_to_mutate == "short_window":
            current_lw = self._get_param_from_code(code_copy, "long_window") or self.param_ranges["long_window"][0]
            max_sw = current_lw - 1
            min_sw = self.param_ranges["short_window"][0]
            if max_sw < min_sw: max_sw = min_sw # Ensure randint range is valid
            new_val = random.randint(min_sw, max_sw)

        elif param_to_mutate == "long_window":
            current_sw = self._get_param_from_code(code_copy, "short_window") or self.param_ranges["short_window"][0]
            min_lw = current_sw + 1
            max_lw = self.param_ranges["long_window"][1]
            if min_lw > max_lw: min_lw = max_lw # Ensure randint range is valid
            new_val = random.randint(min_lw, max_lw)
            
        mutated_code = self._change_param_in_code(code_copy, param_to_mutate, new_val)
        return mutated_code

    def evolve_population(self, population: List[str], fitness_scores: List[Dict[str, Any]]) -> List[str]:
        if not population or not fitness_scores or len(population) != len(fitness_scores):
             # If inputs are problematic, return the original population or an empty list.
            return population if population else []

        next_generation = []
        
        pop_with_fitness = []
        for i, p_code in enumerate(population):
            fit_val = fitness_scores[i].get(self.primary_fitness_metric, -float('inf'))
            if not isinstance(fit_val, (int, float)) or fit_val != fit_val: # Handles NaN
                fit_val = -float('inf')
            pop_with_fitness.append((p_code, fit_val))
        
        pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
        
        # Elitism
        elite_count = min(self.elitism_count, len(pop_with_fitness))
        for i in range(elite_count):
            next_generation.append(pop_with_fitness[i][0])
            
        # Parent Selection
        selected_parents = self.select_parents(population, fitness_scores)
        if not selected_parents: # Fallback if tournament selection yields nothing
            if pop_with_fitness: # Use best individuals from sorted list
                selected_parents = [p[0] for p in pop_with_fitness[:max(1, len(pop_with_fitness))]]
            else: # Should not happen if initial checks passed, but as a safeguard
                return next_generation if next_generation else population

        if not selected_parents: # If still no parents, can't proceed with crossover/mutation
             return next_generation if next_generation else population


        # Crossover and Mutation
        num_offspring_needed = len(population) - len(next_generation)
        for _ in range(num_offspring_needed):
            parent1 = random.choice(selected_parents)
            parent2 = random.choice(selected_parents)
            
            offspring_code = self.crossover(parent1, parent2)
            
            if random.random() < self.mutation_probability:
                offspring_code = self.mutate(offspring_code)
                
            next_generation.append(offspring_code)
            
        return next_generation

if __name__ == '__main__':
    print("--- EvolutionaryEngine Test ---")
    engine = EvolutionaryEngine(
        tournament_size=3,
        elitism_count=2,
        mutation_probability=0.2
    )

    # Test Parameter Extraction and Changing
    sample_code = str(DEFAULT_STRATEGY_TEMPLATE)
    print(f"Original short_window: {engine._get_param_from_code(sample_code, 'short_window')}")
    sample_code = engine._change_param_in_code(sample_code, "short_window", 15)
    print(f"Changed short_window: {engine._get_param_from_code(sample_code, 'short_window')}")
    
    print(f"Original long_window: {engine._get_param_from_code(sample_code, 'long_window')}")
    sample_code = engine._change_param_in_code(sample_code, "long_window", 45)
    print(f"Changed long_window: {engine._get_param_from_code(sample_code, 'long_window')}")

    print(f"Original quantity: {engine._get_param_from_code(sample_code, 'quantity')}")
    sample_code = engine._change_param_in_code(sample_code, "quantity", 7)
    print(f"Changed quantity: {engine._get_param_from_code(sample_code, 'quantity')}")
    print("---")

    # Initialize Population
    initial_pop_size = 10
    population = engine.initialize_population(initial_pop_size)
    print(f"Initialized population of size: {len(population)}")
    for i, strat_code in enumerate(population[:2]): # Print first 2
        print(f"Strategy {i} params: "
              f"SW={engine._get_param_from_code(strat_code, 'short_window')}, "
              f"LW={engine._get_param_from_code(strat_code, 'long_window')}, "
              f"QTY={engine._get_param_from_code(strat_code, 'quantity')}")
    print("---")

    # Mock Fitness Scores
    mock_fitness_scores = []
    for i in range(initial_pop_size):
        # Ensure primary metric can be missing or non-numeric for robustness test
        score = {engine.primary_fitness_metric: random.uniform(-1.0, 2.5)}
        if i % 3 == 0 : score = {"other_metric": 0.5} # missing primary
        if i % 4 == 0 : score = {engine.primary_fitness_metric: "non_numeric_val"} # non-numeric

        mock_fitness_scores.append(score)

    print(f"Mock fitness scores (first 5): {mock_fitness_scores[:5]}")
    print("---")
    
    # Select Parents
    parents = engine.select_parents(population, mock_fitness_scores)
    print(f"Selected parents count: {len(parents)}")
    if parents:
        print(f"First selected parent params: "
              f"SW={engine._get_param_from_code(parents[0], 'short_window')}, "
              f"LW={engine._get_param_from_code(parents[0], 'long_window')}")
    print("---")

    # Crossover
    if len(parents) >= 2:
        offspring = engine.crossover(parents[0], parents[1])
        print(f"Offspring from crossover params: "
              f"SW={engine._get_param_from_code(offspring, 'short_window')}, "
              f"LW={engine._get_param_from_code(offspring, 'long_window')}, "
              f"QTY={engine._get_param_from_code(offspring, 'quantity')}")
    else:
        print("Not enough parents for crossover test.")
    print("---")

    # Mutate
    if population:
        mutated_strategy = engine.mutate(population[0])
        print("Original strategy for mutation:")
        print(f"  SW={engine._get_param_from_code(population[0], 'short_window')}, "
              f"LW={engine._get_param_from_code(population[0], 'long_window')}, "
              f"QTY={engine._get_param_from_code(population[0], 'quantity')}")
        print("Mutated strategy:")
        print(f"  SW={engine._get_param_from_code(mutated_strategy, 'short_window')}, "
              f"LW={engine._get_param_from_code(mutated_strategy, 'long_window')}, "
              f"QTY={engine._get_param_from_code(mutated_strategy, 'quantity')}")
    print("---")

    # Evolve Population
    print("Evolving population...")
    next_gen_population = engine.evolve_population(population, mock_fitness_scores)
    print(f"Next generation population size: {len(next_gen_population)}")
    if next_gen_population:
        print("First 2 strategies in next generation:")
        for i, strat_code in enumerate(next_gen_population[:2]):
            print(f"Strategy {i} params: "
                  f"SW={engine._get_param_from_code(strat_code, 'short_window')}, "
                  f"LW={engine._get_param_from_code(strat_code, 'long_window')}, "
                  f"QTY={engine._get_param_from_code(strat_code, 'quantity')}")
    print("--- EvolutionaryEngine Test Complete ---")

    # Test edge case for constraint in initialize_population
    print("\n--- Testing initialize_population edge case for windows ---")
    engine_edge_test = EvolutionaryEngine()
    # Temporarily modify param_ranges to force edge case
    engine_edge_test.param_ranges["short_window"] = (48, 49) 
    engine_edge_test.param_ranges["long_window"] = (10, 50) # LW max is 50
    
    pop_edge = engine_edge_test.initialize_population(5)
    for i, strat_code in enumerate(pop_edge):
        sw = engine_edge_test._get_param_from_code(strat_code, 'short_window')
        lw = engine_edge_test._get_param_from_code(strat_code, 'long_window')
        print(f"Edge Strategy {i}: SW={sw}, LW={lw}")
        if sw is not None and lw is not None:
            assert sw < lw, f"Constraint failed: SW={sw} not less than LW={lw}"
            assert sw <= engine_edge_test.param_ranges["short_window"][1]
            assert lw <= engine_edge_test.param_ranges["long_window"][1]
    print("--- Edge case test complete ---")

    print("\n--- Testing crossover edge case for windows ---")
    # Parent 1: high SW, Parent 2: low LW (relative to P1 SW)
    parent1_code_edge = engine._change_param_in_code(str(DEFAULT_STRATEGY_TEMPLATE), "short_window", 48)
    parent1_code_edge = engine._change_param_in_code(parent1_code_edge, "long_window", 49) # Valid
    parent2_code_edge = engine._change_param_in_code(str(DEFAULT_STRATEGY_TEMPLATE), "short_window", 10)
    parent2_code_edge = engine._change_param_in_code(parent2_code_edge, "long_window", 12) # Valid

    # Crossover takes SW from P1 (48) and LW from P2 (12)
    # This should trigger the constraint lw2 <= sw1
    offspring_edge = engine.crossover(parent1_code_edge, parent2_code_edge)
    sw_off_edge = engine._get_param_from_code(offspring_edge, 'short_window')
    lw_off_edge = engine._get_param_from_code(offspring_edge, 'long_window')
    print(f"Offspring Edge Case: SW={sw_off_edge}, LW={lw_off_edge}")
    if sw_off_edge is not None and lw_off_edge is not None:
        assert sw_off_edge < lw_off_edge, f"Crossover Constraint failed: SW={sw_off_edge} not less than LW={lw_off_edge}"
    print("--- Crossover edge case test complete ---")

    print("\n--- Testing mutate edge case for windows ---")
    # Case 1: Mutate short_window when long_window is small
    strat_mutate_sw = engine._change_param_in_code(str(DEFAULT_STRATEGY_TEMPLATE), "short_window", 5)
    strat_mutate_sw = engine._change_param_in_code(strat_mutate_sw, "long_window", 6) # LW is very small
    
    mutated_strat_sw = engine.mutate(strat_mutate_sw) # Mutate, hoping it hits short_window
    sw_mut_sw = engine._get_param_from_code(mutated_strat_sw, 'short_window')
    lw_mut_sw = engine._get_param_from_code(mutated_strat_sw, 'long_window')
    print(f"Mutated SW: Original LW=6, New SW={sw_mut_sw}, New LW={lw_mut_sw} (LW may also change if it was mutated)")
    if engine._get_param_from_code(strat_mutate_sw, "long_window") == lw_mut_sw and sw_mut_sw is not None and lw_mut_sw is not None: # if LW wasn't mutated
        assert sw_mut_sw < lw_mut_sw, f"Mutate SW Constraint failed: SW={sw_mut_sw} not less than LW={lw_mut_sw}"

    # Case 2: Mutate long_window when short_window is large
    strat_mutate_lw = engine._change_param_in_code(str(DEFAULT_STRATEGY_TEMPLATE), "short_window", 48)
    strat_mutate_lw = engine._change_param_in_code(strat_mutate_lw, "long_window", 49) # SW is very large
    
    mutated_strat_lw = engine.mutate(strat_mutate_lw) # Mutate, hoping it hits long_window
    sw_mut_lw = engine._get_param_from_code(mutated_strat_lw, 'short_window')
    lw_mut_lw = engine._get_param_from_code(mutated_strat_lw, 'long_window')
    print(f"Mutated LW: Original SW=48, New SW={sw_mut_lw} (SW may also change), New LW={lw_mut_lw}")
    if engine._get_param_from_code(strat_mutate_lw, "short_window") == sw_mut_lw and sw_mut_lw is not None and lw_mut_lw is not None: # if SW wasn't mutated
         assert sw_mut_lw < lw_mut_lw, f"Mutate LW Constraint failed: SW={sw_mut_lw} not less than LW={lw_mut_lw}"
    print("--- Mutate edge case test complete ---")
