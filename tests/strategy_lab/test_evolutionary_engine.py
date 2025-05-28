import unittest
import random
import re
from unittest.mock import patch, MagicMock

from src.strategy_lab.evolutionary_engine import EvolutionaryEngine, DEFAULT_STRATEGY_TEMPLATE

class TestEvolutionaryEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EvolutionaryEngine()
        self.default_code = DEFAULT_STRATEGY_TEMPLATE

    def test_get_param_from_code(self):
        # Test with DEFAULT_STRATEGY_TEMPLATE
        sw = self.engine._get_param_from_code(self.default_code, "short_window")
        lw = self.engine._get_param_from_code(self.default_code, "long_window")
        qty = self.engine._get_param_from_code(self.default_code, "quantity")
        self.assertEqual(sw, 5)  # Corrected from 10 to 5
        self.assertEqual(lw, 10) # Corrected from 20 to 10
        self.assertEqual(qty, 1)   # Corrected from 100 to 1

        # Test with modified code string using the expected "self.param = value" format
        modified_code = """
class SomeStrategyCode:
    def __init__(self, config): # Added config to match one pattern
        # --- PARAM START ---
        self.short_window = self.config.get("short_window", 5) # Uses config.get style
        self.long_window = 15 # Uses direct assignment style
        self.quantity = self.config.get("quantity", 50)
        self.other_param = 123
        # --- PARAM END ---
"""
        # Test extraction for self.short_window = self.config.get("short_window", 5)
        sw_mod_config = self.engine._get_param_from_code(modified_code, "short_window")
        self.assertEqual(sw_mod_config, 5)

        # Test extraction for self.long_window = 15
        lw_mod = self.engine._get_param_from_code(modified_code, "long_window")
        qty_mod_config = self.engine._get_param_from_code(modified_code, "quantity")
        self.assertEqual(lw_mod, 15)
        self.assertEqual(qty_mod_config, 50)

        # Test when a parameter is missing
        missing_param = self.engine._get_param_from_code(self.default_code, "non_existent_param")
        self.assertIsNone(missing_param) # This should still work as expected

        # Test with a different assignment format (direct assignment `self.param = value`)
        # This is already covered by the 'long_window' in modified_code.
        # Let's add a specific test for a code string that *only* uses direct assignment for clarity.
        code_direct_assign_only = """
class AnotherStrategy:
    def __init__(self):
        self.short_window = 7
        self.long_window = 17
        self.quantity = 70
"""
        sw_direct = self.engine._get_param_from_code(code_direct_assign_only, "short_window")
        lw_direct = self.engine._get_param_from_code(code_direct_assign_only, "long_window")
        qty_direct = self.engine._get_param_from_code(code_direct_assign_only, "quantity")
        self.assertEqual(sw_direct, 7)
        self.assertEqual(lw_direct, 17)
        self.assertEqual(qty_direct, 70)

    def test_change_param_in_code(self):
        # Default values from DEFAULT_STRATEGY_TEMPLATE
        default_sw = 5
        default_lw = 10
        default_qty = 1

        # Test changing short_window
        new_sw_val = 7
        new_sw_code = self.engine._change_param_in_code(self.default_code, "short_window", new_sw_val)
        self.assertEqual(self.engine._get_param_from_code(new_sw_code, "short_window"), new_sw_val)
        self.assertEqual(self.engine._get_param_from_code(new_sw_code, "long_window"), default_lw) # Original long_window
        self.assertEqual(self.engine._get_param_from_code(new_sw_code, "quantity"), default_qty) # Original quantity

        # Test changing long_window
        new_lw_val = 30
        new_lw_code = self.engine._change_param_in_code(self.default_code, "long_window", new_lw_val)
        self.assertEqual(self.engine._get_param_from_code(new_lw_code, "short_window"), default_sw) # Original short_window
        self.assertEqual(self.engine._get_param_from_code(new_lw_code, "long_window"), new_lw_val)
        self.assertEqual(self.engine._get_param_from_code(new_lw_code, "quantity"), default_qty) # Original quantity

        # Test changing quantity
        new_qty_val = 200
        new_qty_code = self.engine._change_param_in_code(self.default_code, "quantity", new_qty_val)
        self.assertEqual(self.engine._get_param_from_code(new_qty_code, "short_window"), default_sw) # Original short_window
        self.assertEqual(self.engine._get_param_from_code(new_qty_code, "long_window"), default_lw) # Original long_window
        self.assertEqual(self.engine._get_param_from_code(new_qty_code, "quantity"), new_qty_val)

        # Test changing a non-existent parameter (should return original code)
        no_change_code = self.engine._change_param_in_code(self.default_code, "non_existent_param", 500)
        self.assertEqual(no_change_code, self.default_code)

        # Ensure other parts of the code remain unchanged
        original_lines = self.default_code.splitlines()
        changed_lines_sw = new_sw_code.splitlines()

        # Find the line with "params = {"
        params_line_index_orig = -1
        for i, line in enumerate(original_lines):
            if "params = {" in line:
                params_line_index_orig = i
                break
        
        params_line_index_changed = -1
        for i, line in enumerate(changed_lines_sw):
            if "params = {" in line:
                params_line_index_changed = i
                break

        self.assertEqual(params_line_index_orig, params_line_index_changed)

        # Check lines before params dict (excluding comment lines that might be modified by _change_param_in_code)
        for i in range(params_line_index_orig):
            if not original_lines[i].strip().startswith("#"):
                 self.assertEqual(original_lines[i], changed_lines_sw[i])

        # Check lines after params dict (ignoring lines that define the changed parameter)
        # We need to find the closing '}' of the params dictionary
        params_end_line_orig = -1
        for i in range(params_line_index_orig + 1, len(original_lines)):
            if "}" in original_lines[i]:
                params_end_line_orig = i
                break
        
        params_end_line_changed = -1
        for i in range(params_line_index_changed + 1, len(changed_lines_sw)):
            if "}" in changed_lines_sw[i]:
                params_end_line_changed = i
                break
        
        self.assertEqual(params_end_line_orig, params_end_line_changed)

        for i in range(params_end_line_orig + 1, len(original_lines)):
             self.assertEqual(original_lines[i], changed_lines_sw[i + (params_end_line_changed - params_end_line_orig)])

    def test_initialize_population(self):
        population_size = 10
        population = self.engine.initialize_population(population_size)
        self.assertEqual(len(population), population_size)

        for strategy_code in population:
            self.assertIsInstance(strategy_code, str)
            self.assertTrue(len(strategy_code) > 0)

            sw = self.engine._get_param_from_code(strategy_code, "short_window")
            lw = self.engine._get_param_from_code(strategy_code, "long_window")
            qty = self.engine._get_param_from_code(strategy_code, "quantity")

            self.assertIsNotNone(sw)
            self.assertIsNotNone(lw)
            self.assertIsNotNone(qty)

            self.assertTrue(self.engine.param_ranges['short_window'][0] <= sw <= self.engine.param_ranges['short_window'][1])
            self.assertTrue(self.engine.param_ranges['long_window'][0] <= lw <= self.engine.param_ranges['long_window'][1])
            self.assertTrue(self.engine.param_ranges['quantity'][0] <= qty <= self.engine.param_ranges['quantity'][1])
            self.assertTrue(sw < lw, f"Constraint sw < lw violated: sw={sw}, lw={lw}, code:\n{strategy_code}")

    def test_select_parents_tournament(self):
        engine = EvolutionaryEngine(tournament_size=3)
        population = [f"strategy_{i}" for i in range(5)] # s0, s1, s2, s3, s4
        # Ensure fitness scores are distinct and create a clear ranking
        fitness_scores = [
            {'sharpe_ratio': 0.5}, # s0
            {'sharpe_ratio': 1.5}, # s1
            {'sharpe_ratio': 2.5}, # s2 (fittest in first mocked tournament)
            {'sharpe_ratio': 0.2}, # s3
            {'sharpe_ratio': 1.8}  # s4 (fittest in second mocked tournament)
        ]

        # Mock random.sample to control tournament participants
        # We need to select 5 parents. Each tournament picks one parent.
        # So random.sample will be called 5 times.
        # Tournament 1: s0, s1, s2 -> winner s2
        # Tournament 2: s3, s4, s0 -> winner s4
        # Tournament 3: s1, s2, s3 -> winner s2
        # Tournament 4: s4, s0, s1 -> winner s4
        # Tournament 5: s2, s3, s4 -> winner s2
        with patch('random.sample') as mock_sample:
            mock_sample.side_effect = [
                [(population[0], fitness_scores[0]), (population[1], fitness_scores[1]), (population[2], fitness_scores[2])],
                [(population[3], fitness_scores[3]), (population[4], fitness_scores[4]), (population[0], fitness_scores[0])],
                [(population[1], fitness_scores[1]), (population[2], fitness_scores[2]), (population[3], fitness_scores[3])],
                [(population[4], fitness_scores[4]), (population[0], fitness_scores[0]), (population[1], fitness_scores[1])],
                [(population[2], fitness_scores[2]), (population[3], fitness_scores[3]), (population[4], fitness_scores[4])],
            ]
            parents = engine.select_parents(population, fitness_scores)
            self.assertEqual(len(parents), len(population))
            self.assertEqual(mock_sample.call_count, len(population))
            
            # Expected winners based on side_effect and fitness_scores
            expected_parents = [population[2], population[4], population[2], population[4], population[2]]
            self.assertEqual(parents, expected_parents)

        # Edge Case: Empty population and fitness_scores
        empty_parents = engine.select_parents([], [])
        self.assertEqual(empty_parents, [])

        # Edge Case: All individuals have same fitness
        population_same_fitness = [f"s_same_{i}" for i in range(3)]
        fitness_same = [{'sharpe_ratio': 1.0}] * 3
        # No need to mock random.sample here, just check counts and types
        # We can't predict the exact parents, but we can check if they are from the population
        with patch('random.sample') as mock_sample_same:
             # Make sure each tournament consists of distinct individuals if possible
            mock_sample_same.side_effect = [
                [(population_same_fitness[0], fitness_same[0]), (population_same_fitness[1], fitness_same[1]), (population_same_fitness[2], fitness_same[2])],
                [(population_same_fitness[0], fitness_same[0]), (population_same_fitness[1], fitness_same[1]), (population_same_fitness[2], fitness_same[2])],
                [(population_same_fitness[0], fitness_same[0]), (population_same_fitness[1], fitness_same[1]), (population_same_fitness[2], fitness_same[2])],
            ]
            parents_same_fitness = engine.select_parents(population_same_fitness, fitness_same)
            self.assertEqual(len(parents_same_fitness), len(population_same_fitness))
            for parent in parents_same_fitness:
                self.assertIn(parent, population_same_fitness)

    def test_crossover_parameter_swap(self):
        # Parent 1 parameters
        p1_sw_val = 10
        p1_lw_val = 20
        p1_qty_val = 100
        parent1_code = self.engine._change_param_in_code(self.default_code, "short_window", p1_sw_val)
        parent1_code = self.engine._change_param_in_code(parent1_code, "long_window", p1_lw_val)
        parent1_code = self.engine._change_param_in_code(parent1_code, "quantity", p1_qty_val)

        # Parent 2 parameters
        p2_sw_val = 15
        p2_lw_val = 30 # This will be swapped into offspring
        p2_qty_val = 200
        parent2_code = self.engine._change_param_in_code(self.default_code, "short_window", p2_sw_val)
        parent2_code = self.engine._change_param_in_code(parent2_code, "long_window", p2_lw_val)
        parent2_code = self.engine._change_param_in_code(parent2_code, "quantity", p2_qty_val)

        offspring_code = self.engine.crossover(parent1_code, parent2_code)

        off_sw = self.engine._get_param_from_code(offspring_code, "short_window")
        off_lw = self.engine._get_param_from_code(offspring_code, "long_window")
        off_qty = self.engine._get_param_from_code(offspring_code, "quantity")

        self.assertEqual(off_sw, p1_sw_val) # Takes short_window from parent1
        self.assertEqual(off_lw, p2_lw_val) # Takes long_window from parent2
        self.assertEqual(off_qty, p1_qty_val) # Takes quantity from parent1
        self.assertTrue(off_sw < off_lw)

        # Test constraint check: sw1 >= lw2
        p1_sw_constrained_val = 35
        p1_lw_constrained_val = 45 # Does not matter for this test point
        p1_qty_constrained_val = 110

        p2_sw_constrained_val = 5 # Does not matter
        p2_lw_constrained_val = 25 # Problematic: p1_sw_constrained_val (35) > this (25)
        p2_qty_constrained_val = 220

        parent1_constrained_code = self.engine._change_param_in_code(self.default_code, "short_window", p1_sw_constrained_val)
        parent1_constrained_code = self.engine._change_param_in_code(parent1_constrained_code, "long_window", p1_lw_constrained_val)
        parent1_constrained_code = self.engine._change_param_in_code(parent1_constrained_code, "quantity", p1_qty_constrained_val)

        parent2_constrained_code = self.engine._change_param_in_code(self.default_code, "short_window", p2_sw_constrained_val)
        parent2_constrained_code = self.engine._change_param_in_code(parent2_constrained_code, "long_window", p2_lw_constrained_val)
        parent2_constrained_code = self.engine._change_param_in_code(parent2_constrained_code, "quantity", p2_qty_constrained_val)
        
        offspring_constrained_code = self.engine.crossover(parent1_constrained_code, parent2_constrained_code)

        off_sw_constrained = self.engine._get_param_from_code(offspring_constrained_code, "short_window")
        off_lw_constrained = self.engine._get_param_from_code(offspring_constrained_code, "long_window")
        off_qty_constrained = self.engine._get_param_from_code(offspring_constrained_code, "quantity")

        self.assertEqual(off_sw_constrained, p1_sw_constrained_val)
        # lw from parent2 (25) is <= sw from parent1 (35).
        # The crossover logic will call: random.randint(sw1 + 1, max_lw_val)
        # sw1 + 1 = 36. max_lw_val = 50 (default).
        # We mock randint to control the outcome. Let's say it picks sw1 + 1.
        expected_lw_constrained = p1_sw_constrained_val + 1
        with patch('random.randint', return_value=expected_lw_constrained) as mock_randint_crossover_constraint:
            offspring_constrained_code_rerun = self.engine.crossover(parent1_constrained_code, parent2_constrained_code)
            off_lw_constrained_rerun = self.engine._get_param_from_code(offspring_constrained_code_rerun, "long_window")
            off_sw_constrained_rerun = self.engine._get_param_from_code(offspring_constrained_code_rerun, "short_window")
            off_qty_constrained_rerun = self.engine._get_param_from_code(offspring_constrained_code_rerun, "quantity")

            self.assertEqual(off_sw_constrained_rerun, p1_sw_constrained_val)
            self.assertEqual(off_lw_constrained_rerun, expected_lw_constrained)
            self.assertEqual(off_qty_constrained_rerun, p1_qty_constrained_val)
            self.assertTrue(off_sw_constrained_rerun < off_lw_constrained_rerun)


        # Test constraint check: sw1 >= lw2 and sw1 + 1 > max_long_window
        # Max long window is self.engine.param_ranges['long_window'][1] (default 100)
        max_lw = self.engine.param_ranges['long_window'][1]
        p1_sw_max_lw_val = max_lw -1 # e.g. 99 if max_lw is 100
        p2_lw_max_lw_val = max_lw - 5 # e.g. 95, which is < p1_sw_max_lw_val

        parent1_max_lw_code = self.engine._change_param_in_code(self.default_code, "short_window", p1_sw_max_lw_val)
        parent1_max_lw_code = self.engine._change_param_in_code(parent1_max_lw_code, "long_window", max_lw) # p1_lw doesn't matter
        parent2_max_lw_code = self.engine._change_param_in_code(self.default_code, "long_window", p2_lw_max_lw_val)
        
        # Ensure p1_sw_max_lw_val is indeed >= p2_lw_max_lw_val
        self.assertTrue(p1_sw_max_lw_val >= p2_lw_max_lw_val)

        offspring_max_lw_code = self.engine.crossover(parent1_max_lw_code, parent2_max_lw_code)
        off_sw_max_lw = self.engine._get_param_from_code(offspring_max_lw_code, "short_window")
        off_lw_max_lw = self.engine._get_param_from_code(offspring_max_lw_code, "long_window")
        
        self.assertEqual(off_sw_max_lw, p1_sw_max_lw_val)
        # lw from parent2 (p2_lw_max_lw_val) is <= sw from parent1 (p1_sw_max_lw_val)
        # sw1 + 1 would be p1_sw_max_lw_val + 1 = (max_lw - 1) + 1 = max_lw
        # So, off_lw_max_lw should be max_lw. Here, sw1+1 = max_lw, so randint(max_lw, max_lw) will be called.
        with patch('random.randint', return_value=max_lw) as mock_randint_crossover_max_lw:
            offspring_max_lw_code_rerun = self.engine.crossover(parent1_max_lw_code, parent2_max_lw_code)
            off_sw_max_lw_rerun = self.engine._get_param_from_code(offspring_max_lw_code_rerun, "short_window")
            off_lw_max_lw_rerun = self.engine._get_param_from_code(offspring_max_lw_code_rerun, "long_window")

            self.assertEqual(off_sw_max_lw_rerun, p1_sw_max_lw_val)
            self.assertEqual(off_lw_max_lw_rerun, max_lw)
            self.assertTrue(off_sw_max_lw_rerun < off_lw_max_lw_rerun)


        # Test constraint check: sw1 >= lw2 and sw1 + 1 > max_long_window, and sw1 == max_long_window -1
        # This case is covered above, but if sw1 = max_lw, then sw1+1 > max_lw.
        # The code has: lw_val2 = min(sw_val1 + 1, self.param_ranges['long_window'][1])
        # If sw_val1 = max_lw, then sw_val1 + 1 = max_lw + 1.
        # So lw_val2 = min(max_lw + 1, max_lw) = max_lw. This seems correct.
        # What if sw_val1 itself is already >= max_lw? _change_param_in_code should prevent this.
        # Let's test the case where sw1 = max_lw -1, so sw1+1 = max_lw
        # This was essentially the previous test.

        # Consider a different edge case: sw1 is already at max_short_window
        # And max_short_window = max_long_window -1.
        # Then sw1+1 = max_long_window.
        # This is fine. The logic seems to handle capping at max_long_window correctly.

    def test_mutate_parameter_change(self):
        strategy_code = self.default_code
        orig_sw = self.engine._get_param_from_code(strategy_code, "short_window") # Should be 5
        orig_lw = self.engine._get_param_from_code(strategy_code, "long_window") # Should be 10
        orig_qty = self.engine._get_param_from_code(strategy_code, "quantity")   # Should be 1

        # Test mutating short_window
        # Try to change short_window from 5 to 7 (orig_sw + 2)
        # Ensure new_sw_val (7) < orig_lw (10)
        new_sw_mutation_val = orig_sw + 2 
        self.assertTrue(new_sw_mutation_val < orig_lw) # 7 < 10, this is fine
        with patch('random.choice', return_value="short_window"), \
             patch('random.randint', return_value=new_sw_mutation_val) as mock_randint_sw:
            
            mutated_code = self.engine.mutate(strategy_code)
            mut_sw = self.engine._get_param_from_code(mutated_code, "short_window")
            mut_lw = self.engine._get_param_from_code(mutated_code, "long_window")
            mut_qty = self.engine._get_param_from_code(mutated_code, "quantity")

            self.assertEqual(mut_sw, new_sw_mutation_val)
            self.assertEqual(mut_lw, orig_lw)
            self.assertEqual(mut_qty, orig_qty)
            self.assertTrue(mut_sw < mut_lw)
            self.assertTrue(self.engine.param_ranges['short_window'][0] <= mut_sw <= self.engine.param_ranges['short_window'][1])

        # Test mutating long_window
        # Try to change long_window from 10 to 15 (orig_lw + 5)
        # Ensure new_lw_val (15) > orig_sw (5)
        new_lw_mutation_val = orig_lw + 5
        self.assertTrue(new_lw_mutation_val > orig_sw) # 15 > 5, this is fine
        with patch('random.choice', return_value="long_window"), \
             patch('random.randint', return_value=new_lw_mutation_val) as mock_randint_lw:

            mutated_code = self.engine.mutate(strategy_code)
            mut_sw = self.engine._get_param_from_code(mutated_code, "short_window")
            mut_lw = self.engine._get_param_from_code(mutated_code, "long_window")
            mut_qty = self.engine._get_param_from_code(mutated_code, "quantity")

            self.assertEqual(mut_lw, new_lw_mutation_val)
            self.assertEqual(mut_sw, orig_sw)
            self.assertEqual(mut_qty, orig_qty)
            self.assertTrue(mut_sw < mut_lw) # 5 < 15
            self.assertTrue(self.engine.param_ranges['long_window'][0] <= mut_lw <= self.engine.param_ranges['long_window'][1])

        # Test mutating quantity
        # Try to change quantity from 1 to 5 (orig_qty + 4)
        new_qty_mutation_val = orig_qty + 4
        with patch('random.choice', return_value="quantity"), \
             patch('random.randint', return_value=new_qty_mutation_val) as mock_randint_qty:
            mutated_code = self.engine.mutate(strategy_code)
            mut_sw = self.engine._get_param_from_code(mutated_code, "short_window")
            mut_lw = self.engine._get_param_from_code(mutated_code, "long_window")
            mut_qty = self.engine._get_param_from_code(mutated_code, "quantity")

            self.assertEqual(mut_qty, new_qty_mutation_val)
            self.assertEqual(mut_sw, orig_sw)
            self.assertEqual(mut_lw, orig_lw)
            self.assertTrue(self.engine.param_ranges['quantity'][0] <= mut_qty <= self.engine.param_ranges['quantity'][1])

        # Constraint Check: Mutating short_window to be >= current_lw
        # Constraint Check: Mutating short_window to be >= current_lw
        # Assumes mutate calls randint ONCE, then clamps.
        code_sw_constraint = self.engine._change_param_in_code(self.default_code, "short_window", 7) 
        code_sw_constraint = self.engine._change_param_in_code(code_sw_constraint, "long_window", 8)   
        current_lw_val = self.engine._get_param_from_code(code_sw_constraint, "long_window") # is 8
        expected_constrained_sw = current_lw_val - 1 # Should be 7

        with patch('random.choice', return_value="short_window"), \
             patch('random.randint') as mock_rand_int_sw_constraint:
            mock_rand_int_sw_constraint.return_value = 10 # Attempt to set sw to 10 (problematic)
            
            mutated_sw_constraint_code = self.engine.mutate(code_sw_constraint)
            mut_sw = self.engine._get_param_from_code(mutated_sw_constraint_code, "short_window")
            mut_lw = self.engine._get_param_from_code(mutated_sw_constraint_code, "long_window")

            self.assertEqual(mut_sw, expected_constrained_sw) # Expect 7
            self.assertEqual(mut_lw, current_lw_val) 
            self.assertEqual(mock_rand_int_sw_constraint.call_count, 1)


        # Constraint Check: Mutating long_window to be <= current_sw
        # Assumes mutate calls randint ONCE, then clamps.
        code_lw_constraint = self.engine._change_param_in_code(self.default_code, "short_window", 7) 
        code_lw_constraint = self.engine._change_param_in_code(code_lw_constraint, "long_window", 8)   
        current_sw_val = self.engine._get_param_from_code(code_lw_constraint, "short_window") # is 7
        expected_constrained_lw = current_sw_val + 1 # Should be 8

        with patch('random.choice', return_value="long_window"), \
             patch('random.randint') as mock_rand_int_lw_constraint:
            mock_rand_int_lw_constraint.return_value = 6 # Attempt to set lw to 6 (problematic)
            
            mutated_lw_constraint_code = self.engine.mutate(code_lw_constraint)
            mut_sw = self.engine._get_param_from_code(mutated_lw_constraint_code, "short_window")
            mut_lw = self.engine._get_param_from_code(mutated_lw_constraint_code, "long_window")

            self.assertEqual(mut_sw, current_sw_val) 
            self.assertEqual(mut_lw, expected_constrained_lw) # Expect 8
            self.assertEqual(mock_rand_int_lw_constraint.call_count, 1)

        # Constraint Check: Mutating short_window to violate lower bound (e.g., 0 or less)
        # This test now assumes mutate() calls random.randint ONCE for initial value, then applies direct clamping.
        min_sw_param_range = self.engine.param_ranges['short_window'][0] # This is 3.
        code_min_sw = self.engine._change_param_in_code(self.default_code, "short_window", min_sw_param_range)
        
        attempted_val_too_low = min_sw_param_range - 1 # 2
        expected_clamped_val = min_sw_param_range    # 3

        with patch('random.choice', return_value="short_window"), \
             patch('random.randint') as mock_rand_int_min_sw_lower:
            mock_rand_int_min_sw_lower.return_value = attempted_val_too_low # random.randint will return 2
            
            mutated_code = self.engine.mutate(code_min_sw)
            
            mut_sw = self.engine._get_param_from_code(mutated_code, "short_window")
            self.assertEqual(mut_sw, expected_clamped_val) # Expected: self.assertEqual(3, 3)
            self.assertEqual(mock_rand_int_min_sw_lower.call_count, 1)


        # Constraint Check: Mutating long_window to violate upper bound
        # This test also assumes mutate() calls random.randint ONCE for initial value, then applies direct clamping.
        max_lw_param_range = self.engine.param_ranges['long_window'][1] # Default is 50
        code_max_lw = self.engine._change_param_in_code(self.default_code, "long_window", max_lw_param_range) 
        
        attempted_val_too_high = max_lw_param_range + 5 # 55
        expected_clamped_lw_val = max_lw_param_range  # 50
        
        with patch('random.choice', return_value="long_window"), \
             patch('random.randint') as mock_rand_int_max_lw_upper:
            mock_rand_int_max_lw_upper.return_value = attempted_val_too_high # random.randint will return 55

            mutated_code_max_lw = self.engine.mutate(code_max_lw)

            mut_lw = self.engine._get_param_from_code(mutated_code_max_lw, "long_window")
            self.assertEqual(mut_lw, expected_clamped_lw_val) # Expected: self.assertEqual(50,50)
            self.assertEqual(mock_rand_int_max_lw_upper.call_count, 1)

    @patch.object(EvolutionaryEngine, 'mutate')
    @patch.object(EvolutionaryEngine, 'crossover')
    @patch.object(EvolutionaryEngine, 'select_parents')
    def test_evolve_population(self, mock_select_parents, mock_crossover, mock_mutate):
        engine = EvolutionaryEngine(elitism_count=1, mutation_probability=0.5)
        population = [f"s{i}_{random.randint(100,200)}" for i in range(5)] # Unique codes
        # s2 is the fittest
        fitness_scores = [
            {'sharpe_ratio': 0.5, 'total_trades': 10, 'winning_trades': 5, 'losing_trades':5 , 'avg_profit':100, 'max_drawdown':50, 'code': population[0]},
            {'sharpe_ratio': 1.5, 'total_trades': 10, 'winning_trades': 5, 'losing_trades':5 , 'avg_profit':100, 'max_drawdown':50, 'code': population[1]},
            {'sharpe_ratio': 2.5, 'total_trades': 10, 'winning_trades': 5, 'losing_trades':5 , 'avg_profit':100, 'max_drawdown':50, 'code': population[2]}, # Fittest
            {'sharpe_ratio': 0.2, 'total_trades': 10, 'winning_trades': 5, 'losing_trades':5 , 'avg_profit':100, 'max_drawdown':50, 'code': population[3]},
            {'sharpe_ratio': 1.8, 'total_trades': 10, 'winning_trades': 5, 'losing_trades':5 , 'avg_profit':100, 'max_drawdown':50, 'code': population[4]}
        ]
        fittest_individual_code = population[2]

        # Mock setup
        mock_select_parents.return_value = [population[0], population[1], population[2], population[3], population[4]] # Example parent list
        
        # Test with mutation occurring
        with patch('random.random', return_value=0.4): # Force mutation
            # Reset mocks for this specific scenario if they are stateful from previous tests or runs
            mock_crossover.reset_mock()
            mock_mutate.reset_mock()
            mock_crossover.side_effect = [f"crossed_over_strategy_{i}" for i in range(len(population) - engine.elitism_count)]
            mock_mutate.side_effect = [f"mutated_strategy_{i}" for i in range(len(population) - engine.elitism_count)]

            next_gen = engine.evolve_population(population, fitness_scores)
            
            self.assertEqual(len(next_gen), len(population))
            self.assertIn(fittest_individual_code, next_gen)
            mock_select_parents.assert_called_once_with(population, fitness_scores)
            self.assertEqual(mock_crossover.call_count, len(population) - engine.elitism_count)
            self.assertEqual(mock_mutate.call_count, len(population) - engine.elitism_count)
            
            # Check if mutated strategies are in the next generation (excluding the elite one)
            mutated_count_in_next_gen = 0
            for i in range(len(population) - engine.elitism_count):
                if f"mutated_strategy_{i}" in next_gen:
                    mutated_count_in_next_gen +=1
            self.assertEqual(mutated_count_in_next_gen, len(population) - engine.elitism_count)

        # Test with no mutation occurring
        mock_select_parents.reset_mock() # Reset for the next call
        mock_crossover.reset_mock()
        mock_mutate.reset_mock()
        mock_select_parents.return_value = [population[0], population[1], population[2], population[3], population[4]]
        mock_crossover.side_effect = [f"crossed_over_no_mutate_{i}" for i in range(len(population) - engine.elitism_count)]
        # If mutate is called, it should return the input if random.random is high
        # The current EvolutionaryEngine.mutate always returns a new string object due to _change_param_in_code.
        # So, we'll have mock_mutate return the string it was given.
        def mutate_passthrough(code_string, mutation_prob_arg_ignored): # Mocking internal mutate's behavior with no actual mutation
             return code_string
        # The evolve_population method itself checks random.random() < self.mutation_probability
        # So if random.random() is high, engine.mutate is not called.

        with patch('random.random', return_value=0.6): # Prevent mutation
            next_gen_no_mutate = engine.evolve_population(population, fitness_scores)

            self.assertEqual(len(next_gen_no_mutate), len(population))
            self.assertIn(fittest_individual_code, next_gen_no_mutate)
            mock_select_parents.assert_called_once_with(population, fitness_scores) # Called again
            self.assertEqual(mock_crossover.call_count, len(population) - engine.elitism_count)
            self.assertEqual(mock_mutate.call_count, 0) # Mutate should not be called by evolve_population

            # Check if crossed-over (but not mutated) strategies are in the next generation
            crossed_over_count_in_next_gen = 0
            for i in range(len(population) - engine.elitism_count):
                if f"crossed_over_no_mutate_{i}" in next_gen_no_mutate:
                    crossed_over_count_in_next_gen +=1
            self.assertEqual(crossed_over_count_in_next_gen, len(population) - engine.elitism_count)

        # Edge Case: elitism_count >= len(population)
        engine_all_elite = EvolutionaryEngine(elitism_count=len(population), mutation_probability=0.5)
        mock_select_parents.reset_mock()
        mock_crossover.reset_mock()
        mock_mutate.reset_mock()
        
        # Sort population by fitness for comparison, as elitism will pick all of them
        # The actual implementation sorts based on fitness_scores, so we expect the codes from sorted fitness_scores
        sorted_fitness_info = sorted(fitness_scores, key=lambda x: x['sharpe_ratio'], reverse=True)
        expected_elite_population = [info['code'] for info in sorted_fitness_info]


        next_gen_all_elite = engine_all_elite.evolve_population(population, fitness_scores)
        self.assertEqual(len(next_gen_all_elite), len(population))
        self.assertEqual(sorted(next_gen_all_elite), sorted(expected_elite_population)) # Order might change based on internal sorting
        mock_select_parents.assert_not_called() # select_parents is not called if all are elite
        mock_crossover.assert_not_called()
        mock_mutate.assert_not_called()

        # Edge Case: Empty population
        engine_empty = EvolutionaryEngine()
        mock_select_parents.reset_mock()
        mock_crossover.reset_mock()
        mock_mutate.reset_mock()
        next_gen_empty = engine_empty.evolve_population([], [])
        self.assertEqual(next_gen_empty, [])
        mock_select_parents.assert_not_called()
        mock_crossover.assert_not_called()
        mock_mutate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
