import unittest
from unittest.mock import patch, MagicMock
import random
import re
from src.strategy_lab.evolutionary_engine import EvolutionaryEngine, DEFAULT_STRATEGY_TEMPLATE

class TestEvolutionaryEngine(unittest.TestCase):
    """
    Test suite for the EvolutionaryEngine class.
    """

    def setUp(self):
        """
        Instantiate EvolutionaryEngine for each test.
        """
        self.engine = EvolutionaryEngine() # Uses default param_ranges

    def _create_code_from_params(self, sw, lw, qty, symbol="TEST"):
        """Helper to create a strategy code string from parameters using engine's methods."""
        code = str(DEFAULT_STRATEGY_TEMPLATE) # Start with a fresh template copy
        # Note: DEFAULT_STRATEGY_TEMPLATE doesn't have {{SYMBOL}}, symbol is set via config.get("symbol", "DEFAULT_SYMBOL")
        # We'll assume the strategy config passed to an EvolvedStrategy instance would handle the symbol.
        # For testing parameter manipulation, we focus on sw, lw, qty.
        code = self.engine._change_param_in_code(code, "short_window", sw)
        code = self.engine._change_param_in_code(code, "long_window", lw)
        code = self.engine._change_param_in_code(code, "quantity", qty)
        return code

    # --- Test initialize_population() ---
    def test_initialize_population(self):
        # 5.a. Call engine.initialize_population(size=5)
        population_size = 5
        population = self.engine.initialize_population(size=population_size)
        
        # 5.b. Assert the returned list has 5 strategy code strings
        self.assertEqual(len(population), population_size)

        # 5.c. For each strategy string:
        for code in population:
            # i. Extract params
            sw = self.engine._get_param_from_code(code, "short_window")
            lw = self.engine._get_param_from_code(code, "long_window")
            qty = self.engine._get_param_from_code(code, "quantity")

            # ii. Assert params are not None
            self.assertIsNotNone(sw, f"short_window was None in code: {code}")
            self.assertIsNotNone(lw, f"long_window was None in code: {code}")
            self.assertIsNotNone(qty, f"quantity was None in code: {code}")

            # iii. Assert sw range
            self.assertTrue(self.engine.param_ranges['short_window'][0] <= sw <= self.engine.param_ranges['short_window'][1], f"sw {sw} out of range")
            # iv. Assert lw range
            self.assertTrue(self.engine.param_ranges['long_window'][0] <= lw <= self.engine.param_ranges['long_window'][1], f"lw {lw} out of range")
            # v. Assert qty range
            self.assertTrue(self.engine.param_ranges['quantity'][0] <= qty <= self.engine.param_ranges['quantity'][1], f"qty {qty} out of range")
            # vi. Assert sw < lw
            self.assertLess(sw, lw, f"Constraint sw < lw failed: sw={sw}, lw={lw} in code: {code}")

    # 5.d. Test the edge case
    def test_initialize_population_edge_case_sw_lw_constraint(self):
        custom_engine = EvolutionaryEngine() # Instantiate with default
        # Set custom param_ranges for this specific test
        custom_engine.param_ranges = {
            'short_window': (48, 49),
            'long_window': (10, 50), 
            'quantity': (1, 10)
        }
        # _ensure_constraints in initialize_population should adjust long_window min if needed.
        # Specifically, min_long_window will be max(param_ranges['long_window'][0], sw + 1).
        # If sw is 49, min_long_window becomes 50.
        
        population = custom_engine.initialize_population(size=20) # Generate a few to increase chance of hitting edges
        for code in population:
            sw = custom_engine._get_param_from_code(code, "short_window")
            lw = custom_engine._get_param_from_code(code, "long_window")
            
            self.assertIsNotNone(sw)
            self.assertIsNotNone(lw)
            self.assertTrue(48 <= sw <= 49)
            # After _ensure_constraints, if sw is 49, lw must be at least 50.
            # The max long_window is 50. So if sw is 49, lw must be 50.
            if sw == 49:
                self.assertEqual(lw, 50, f"If sw=49, lw should be 50 due to constraints. Got lw={lw}")
            
            self.assertTrue(custom_engine.param_ranges['long_window'][0] <= lw <= custom_engine.param_ranges['long_window'][1])
            self.assertLess(sw, lw, f"Edge case constraint sw < lw failed: sw={sw}, lw={lw}")


    # --- Test crossover() ---
    def test_crossover_basic(self):
        # 6.a. Create two parent strategy codes
        p1_sw, p1_lw, p1_qty = 10, 20, 5
        p2_sw, p2_lw, p2_qty = 15, 30, 8
        p1_code = self._create_code_from_params(p1_sw, p1_lw, p1_qty)
        p2_code = self._create_code_from_params(p2_sw, p2_lw, p2_qty)

        # 6.b. Call crossover
        offspring_code = self.engine.crossover(p1_code, p2_code)
        
        # 6.c. Extract params and assert
        off_sw = self.engine._get_param_from_code(offspring_code, "short_window")
        off_lw = self.engine._get_param_from_code(offspring_code, "long_window")
        off_qty = self.engine._get_param_from_code(offspring_code, "quantity")

        self.assertEqual(off_sw, p1_sw) # As per current crossover logic
        self.assertEqual(off_lw, p2_lw) # As per current crossover logic
        self.assertEqual(off_qty, p1_qty) # As per current crossover logic
        self.assertLess(off_sw, off_lw, "Crossover basic: sw < lw constraint failed for offspring.")

    # 6.d. Test the edge case
    def test_crossover_edge_case_sw_lw_constraint(self):
        p1_code = self._create_code_from_params(sw=48, lw=55, qty=1) # p1_sw=48
        p2_code = self._create_code_from_params(sw=5, lw=12, qty=1)  # p2_lw=12

        # Offspring before _ensure_constraints: sw=48, lw=12, qty=1 (from p1)
        # Default engine param_ranges: short_window: (5, 50), long_window: (10, 100)
        offspring_code = self.engine.crossover(p1_code, p2_code)
        
        off_sw = self.engine._get_param_from_code(offspring_code, "short_window") 
        off_lw = self.engine._get_param_from_code(offspring_code, "long_window") 
        
        # _ensure_constraints logic:
        # 1. Clamp sw: 48 is within (5, 50). off_sw = 48.
        # 2. Clamp lw: 12 is within (10, 100). off_lw = 12.
        # 3. Ensure sw < lw: 48 < 12 is false. Adjust lw = sw + 1 = 48 + 1 = 49.
        # 4. Re-clamp lw: 49 is within (10, 100). off_lw = 49.
        self.assertEqual(off_sw, 48)
        self.assertEqual(off_lw, 49) # Adjusted value
        self.assertLess(off_sw, off_lw, "Crossover edge: sw < lw constraint failed post-adjustment.")


    # --- Test mutate() ---
    # 7.a. Create base code
    @patch('random.choice')
    @patch('random.randint')
    def test_mutate_short_window(self, mock_randint, mock_choice):
        # 7.b. Mock random.choice
        mock_choice.return_value = "short_window"
        # 7.c. Mock random.randint
        new_sw_value = 15
        mock_randint.return_value = new_sw_value # This will be the new value for short_window
        
        base_code = self._create_code_from_params(sw=10, lw=30, qty=5)
        # 7.d. Call mutate
        mutated_code = self.engine.mutate(base_code)
        
        # 7.e. Extract and assert
        mut_sw = self.engine._get_param_from_code(mutated_code, "short_window")
        orig_lw = self.engine._get_param_from_code(base_code, "long_window") # Should be 30

        self.assertEqual(mut_sw, new_sw_value)
        # 7.f.i. Verify constraint
        self.assertLess(mut_sw, orig_lw, "Mutated sw should be less than original lw.")

    @patch('random.choice')
    @patch('random.randint')
    def test_mutate_long_window(self, mock_randint, mock_choice):
        mock_choice.return_value = "long_window"
        new_lw_value = 25
        mock_randint.return_value = new_lw_value # New value for long_window

        base_code = self._create_code_from_params(sw=10, lw=20, qty=5)
        mutated_code = self.engine.mutate(base_code)

        mut_lw = self.engine._get_param_from_code(mutated_code, "long_window")
        orig_sw = self.engine._get_param_from_code(base_code, "short_window") # Should be 10
        
        self.assertEqual(mut_lw, new_lw_value)
        # 7.f.ii. Verify constraint
        self.assertGreater(mut_lw, orig_sw, "Mutated lw should be greater than original sw.")

    # 7.f.i Test constraint: new_sw < original_lw (clamping)
    def test_mutate_constraint_sw_less_than_lw_clamping(self):
        base_lw = 22 # original_lw
        base_code = self._create_code_from_params(sw=20, lw=base_lw, qty=1)
        # Try to mutate sw to a value >= base_lw (e.g., 25)
        with patch('random.choice', return_value="short_window"), \
             patch('random.randint', return_value=25): 
            mutated_code = self.engine.mutate(base_code)
        
        mut_sw = self.engine._get_param_from_code(mutated_code, "short_window")
        # Expected: sw is clamped to base_lw - 1 = 21
        self.assertEqual(mut_sw, base_lw - 1)

    # 7.f.ii Test constraint: new_lw > original_sw (clamping)
    def test_mutate_constraint_lw_greater_than_sw_clamping(self):
        base_sw = 18 # original_sw
        base_code = self._create_code_from_params(sw=base_sw, lw=20, qty=1)
        # Try to mutate lw to a value <= base_sw (e.g., 15)
        with patch('random.choice', return_value="long_window"), \
             patch('random.randint', return_value=15):
            mutated_code = self.engine.mutate(base_code)

        mut_lw = self.engine._get_param_from_code(mutated_code, "long_window")
        # Expected: lw is clamped to base_sw + 1 = 19
        self.assertEqual(mut_lw, base_sw + 1)


    # --- Test select_parents() ---
    def test_select_parents_basic(self):
        # 8.a. Create population
        population = [
            self._create_code_from_params(10,20,1), 
            self._create_code_from_params(11,22,1), 
            self._create_code_from_params(12,24,1)
        ]
        # 8.b. Create fitness scores
        fitness_scores = [
            {'Sharpe Ratio': 1.0, 'error': None}, # FitnessEvaluator uses "Sharpe Ratio" key
            {'Sharpe Ratio': 2.0, 'error': None}, 
            {'Sharpe Ratio': 0.5, 'error': None}
        ]
        # 8.c. Set tournament_size
        self.engine.tournament_size = 2
        
        # 8.d. Call select_parents
        parents = self.engine.select_parents(population, fitness_scores)
        # 8.e. Assert size
        self.assertEqual(len(parents), len(population)) 


    # --- Test evolve_population() ---
    def test_evolve_population_structure_and_elitism(self):
        # 9.a. Create population and fitness scores
        population_size = 5
        population = [self._create_code_from_params(10+i, 20+i*2, 1) for i in range(population_size)]
        # Fitness scores where the first individual is the best
        fitness_scores = [
            {'Sharpe Ratio': 1.0 - (i*0.1), 'error': None} for i in range(population_size)
        ] 
        best_individual_code = population[0] # Corresponds to fitness_scores[0]

        # 9.b. Set elitism_count
        self.engine.elitism_count = 1
        self.engine.population_size = population_size 
        
        # Mock crossover and mutate as they are complex and tested separately
        # Ensure they return valid code strings that can be processed by _get_param_from_code
        mock_offspring = self._create_code_from_params(5,10,1) # dummy valid offspring
        
        with patch.object(self.engine, 'select_parents', side_effect=lambda pop, scores: pop), \
             patch.object(self.engine, 'crossover', return_value=mock_offspring), \
             patch.object(self.engine, 'mutate', side_effect=lambda code: code): # Mutate returns code as is
            
            # 9.c. Call evolve_population
            evolved_pop = self.engine.evolve_population(population, fitness_scores)

        # 9.d. Assert length
        self.assertEqual(len(evolved_pop), population_size)
        # 9.e. Assert elitism
        self.assertIn(best_individual_code, evolved_pop, "Best individual (elitism) not found in evolved population.")

if __name__ == '__main__':
    unittest.main()
