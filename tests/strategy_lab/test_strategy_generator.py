import unittest
from unittest.mock import MagicMock, patch, call
import logging # For patching logger

# Import actual classes for spec and for direct use
from src.strategy_lab.strategy_generator import StrategyGenerator
from src.strategy_lab.fitness_evaluator import FitnessEvaluator 
from src.strategy_lab.evolutionary_engine import EvolutionaryEngine
from src.strategy_lab.llm_interface import MockLLMInterface # Corrected import path

class TestStrategyGenerator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_llm_interface = MagicMock(spec=MockLLMInterface)
        
        self.mock_fitness_evaluator = MagicMock(spec=FitnessEvaluator)
        self.mock_evolutionary_engine = MagicMock(spec=EvolutionaryEngine)

        self.initial_population = ["initial_strategy_code_1", "initial_strategy_code_2"]
        self.evolved_population_gen1 = ["evolved_strategy_g1_1", "evolved_strategy_g1_2"]
        self.evolved_population_gen2 = ["evolved_strategy_g2_1", "evolved_strategy_g2_2"]

        self.mock_evolutionary_engine.initialize_population.return_value = self.initial_population
        self.mock_evolutionary_engine.evolve_population.side_effect = [
            self.evolved_population_gen1, 
            self.evolved_population_gen2
        ]
        
        # self.default_fitness_score = {'sharpe_ratio': 1.0, 'total_return': 0.05, 'fitness_score': 1.0}
        # self.mock_fitness_evaluator.evaluate_strategy.return_value = self.default_fitness_score # Removed as per instruction
        
        # This attribute is accessed by StrategyGenerator, so it needs to be on the mock
        self.mock_evolutionary_engine.primary_fitness_metric = 'sharpe_ratio' 

        self.config = {
            'historical_data_path': 'dummy/path/to/data.csv',
            'strategy_config_template': {'symbol': 'TEST_SYM', 'param1': 10},
            'population_size': 2, 
            'num_generations': 3   # num_generations = 3 means 2 evolution steps
        }

        # Patch the logger for StrategyGenerator instances before instantiation
        # self.logger_patcher = patch('src.strategy_lab.strategy_generator.logging.getLogger', return_value=MagicMock())
        # self.mock_logger = self.logger_patcher.start()

        self.generator = StrategyGenerator(
            fitness_evaluator=self.mock_fitness_evaluator,
            evolutionary_engine=self.mock_evolutionary_engine,
            llm_interface=self.mock_llm_interface, 
            config=self.config
        )
        self.mock_logger = MagicMock() 
        self.generator.logger = self.mock_logger 
        
    def tearDown(self):
        # self.logger_patcher.stop()
        pass 

    def test_run_evolution_basic_flow(self):
        """Test the basic flow of the run_evolution method."""
        pop_size = self.config['population_size']
        num_generations = self.config['num_generations']

        fitness_scores_sequence = [
            {'sharpe_ratio': 0.5, 'id': 'g0s0_fit'}, # Corresponds to self.initial_population[0]
            {'sharpe_ratio': 0.6, 'id': 'g0s1_fit'}, # Corresponds to self.initial_population[1]
            {'sharpe_ratio': 0.7, 'id': 'g1s0_fit'}, # Corresponds to self.evolved_population_gen1[0]
            {'sharpe_ratio': 0.8, 'id': 'g1s1_fit'}, # Corresponds to self.evolved_population_gen1[1]
            {'sharpe_ratio': 0.75, 'id': 'g2s0_fit'},# Corresponds to self.evolved_population_gen2[0]
            {'sharpe_ratio': 0.9, 'id': 'g2s1_fit'}  # Corresponds to self.evolved_population_gen2[1]
        ]
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = fitness_scores_sequence

        best_strategy_code, best_fitness = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        expected_eval_calls = pop_size * num_generations
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, expected_eval_calls)
        first_eval_call_args = self.mock_fitness_evaluator.evaluate_strategy.call_args_list[0]
        expected_first_eval_call = call(
            strategy_code_string=self.initial_population[0],
            historical_data_path=self.config['historical_data_path'],
            strategy_config=self.config['strategy_config_template']
        )
        self.assertEqual(first_eval_call_args, expected_first_eval_call)
        self.assertEqual(self.mock_evolutionary_engine.evolve_population.call_count, num_generations -1)
        if num_generations > 1:
            first_evolve_call_args = self.mock_evolutionary_engine.evolve_population.call_args_list[0]
            # The fitness scores passed to evolve_population do not have the 'code' key
            # as this key is added later by the StrategyGenerator for its internal tracking.
            # So, expected_fitness_scores_for_evolve should reflect the direct output 
            # of fitness_evaluator.evaluate_strategy.
            # If specific varying scores were set up for the initial population evaluation, use those.
            # For this test, default_fitness_score is returned for all, so a list of copies is fine.
            expected_fitness_scores_for_evolve = fitness_scores_sequence[:pop_size]
            self.assertEqual(first_evolve_call_args, call(self.initial_population, expected_fitness_scores_for_evolve))
        
        expected_best_code = self.evolved_population_gen2[1]
        expected_best_fitness = fitness_scores_sequence[5]
        
        self.assertEqual(best_strategy_code, expected_best_code)
        self.assertEqual(best_fitness, expected_best_fitness)

    def test_run_evolution_tracks_best_strategy(self):
        pop_size = self.config['population_size']; num_generations = self.config['num_generations'] 
        s_g0i0 = "s_g0i0_code"; s_g0i1 = "s_g0i1_code"
        f_g0i0 = {'sharpe_ratio': 0.5, 'id': 'g0i0'}; f_g0i1 = {'sharpe_ratio': 1.0, 'id': 'g0i1'}
        s_g1i0 = "s_g1i0_code"; s_g1i1 = "s_g1i1_code"
        f_g1i0 = {'sharpe_ratio': 2.5, 'id': 'g1i0'}; f_g1i1 = {'sharpe_ratio': 0.8, 'id': 'g1i1'}
        s_g2i0 = "s_g2i0_code"; s_g2i1 = "s_g2i1_code"
        f_g2i0 = {'sharpe_ratio': 1.5, 'id': 'g2i0'}; f_g2i1 = {'sharpe_ratio': 1.3, 'id': 'g2i1'}
        self.mock_evolutionary_engine.initialize_population.return_value = [s_g0i0, s_g0i1]
        self.mock_evolutionary_engine.evolve_population.side_effect = [[s_g1i0, s_g1i1], [s_g2i0, s_g2i1]]
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [f_g0i0, f_g0i1, f_g1i0, f_g1i1, f_g2i0, f_g2i1]
        best_code, best_fitness = self.generator.run_evolution()
        expected_best_code = s_g1i0; expected_best_fitness_original = f_g1i0
        self.assertEqual(best_code, expected_best_code)
        self.assertEqual(best_fitness, expected_best_fitness_original)
        self.mock_evolutionary_engine.initialize_population.reset_mock(); self.mock_evolutionary_engine.evolve_population.reset_mock(); self.mock_fitness_evaluator.evaluate_strategy.reset_mock()
        f_g0i0_v2 = {'sharpe_ratio': 3.0, 'id': 'g0i0_v2'}; f_g0i1_v2 = {'sharpe_ratio': 1.0, 'id': 'g0i1_v2'}
        f_g1i0_v2 = {'sharpe_ratio': 1.2, 'id': 'g1i0_v2'}; f_g1i1_v2 = {'sharpe_ratio': 0.8, 'id': 'g1i1_v2'}
        f_g2i0_v2 = {'sharpe_ratio': 1.5, 'id': 'g2i0_v2'}; f_g2i1_v2 = {'sharpe_ratio': 1.3, 'id': 'g2i1_v2'}
        self.mock_evolutionary_engine.initialize_population.return_value = [s_g0i0, s_g0i1] 
        self.mock_evolutionary_engine.evolve_population.side_effect = [[s_g1i0, s_g1i1], [s_g2i0, s_g2i1]]
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [f_g0i0_v2, f_g0i1_v2, f_g1i0_v2, f_g1i1_v2, f_g2i0_v2, f_g2i1_v2]
        best_code_v2, best_fitness_v2 = self.generator.run_evolution()
        expected_best_code_v2 = s_g0i0; expected_best_fitness_original_v2 = f_g0i0_v2
        self.assertEqual(best_code_v2, expected_best_code_v2)
        self.assertEqual(best_fitness_v2, expected_best_fitness_original_v2)

    def test_run_evolution_num_generations_edge_cases(self):
        pop_size = self.config['population_size']
        self.generator.config['num_generations'] = 1
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_llm_interface.reset_mock() 
        initial_pop_gen1_run = ["s_g1_i0", "s_g1_i1"]
        fitness_g1_i0 = {'sharpe_ratio': 1.5, 'id': 'g1_i0_fit'}; fitness_g1_i1 = {'sharpe_ratio': 0.5, 'id': 'g1_i1_fit'}
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop_gen1_run
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [fitness_g1_i0, fitness_g1_i1]
        best_code_one_gen, best_fitness_one_gen = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, pop_size)
        self.mock_evolutionary_engine.evolve_population.assert_not_called()
        expected_best_code_one_gen = initial_pop_gen1_run[0] 
        expected_best_fitness_one_gen = fitness_g1_i0.copy()
        self.assertEqual(best_code_one_gen, expected_best_code_one_gen)
        self.assertEqual(best_fitness_one_gen, expected_best_fitness_one_gen)
        self.generator.config['num_generations'] = 0
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock()
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop_gen1_run 
        best_code_zero_gen, best_fitness_zero_gen = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.mock_fitness_evaluator.evaluate_strategy.assert_not_called() # Corrected based on implementation
        self.mock_evolutionary_engine.evolve_population.assert_not_called()
        self.assertIsNone(best_code_zero_gen); self.assertIsNone(best_fitness_zero_gen)

    def test_run_evolution_handles_empty_population(self):
        pop_size = self.config['population_size']
        self.generator.config['num_generations'] = 2 
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_logger.reset_mock()
        self.mock_evolutionary_engine.initialize_population.return_value = []
        best_code_empty_init, best_fitness_empty_init = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.mock_fitness_evaluator.evaluate_strategy.assert_not_called()
        self.mock_evolutionary_engine.evolve_population.assert_not_called()
        self.assertIsNone(best_code_empty_init); self.assertIsNone(best_fitness_empty_init)
        self.mock_logger.error.assert_any_call("EvolutionaryEngine failed to initialize population.")
        
        self.mock_logger.error.assert_any_call("EvolutionaryEngine failed to initialize population.")
        
        # Second part: population becomes empty after evolution
        self.generator.config['num_generations'] = 2 # Ensure it runs for at least one evolution step
        
        # Create and configure a fresh mock for the evolutionary engine
        fresh_mock_evo_engine = MagicMock(spec=EvolutionaryEngine)
        initial_pop_s2 = ("s0_s2", "s1_s2") # Keep as tuple
        fresh_mock_evo_engine.initialize_population.return_value = initial_pop_s2
        fresh_mock_evo_engine.primary_fitness_metric = 'sharpe_ratio' 
        fresh_mock_evo_engine.evolve_population.return_value = []

        # Temporarily replace the generator's evolutionary engine
        original_evo_engine = self.generator.evolutionary_engine
        self.generator.evolutionary_engine = fresh_mock_evo_engine

        # Reset other mocks
        self.mock_fitness_evaluator.reset_mock()
        self.mock_logger.reset_mock()
        
        fitness_s0_s2 = {'sharpe_ratio': 1.0, 'id': 's0_s2_fit'}
        fitness_s1_s2 = {'sharpe_ratio': 0.5, 'id': 's1_s2_fit'}
        
        eval_call_log = [] # To store details of each call
        eval_responses = [fitness_s0_s2, fitness_s1_s2]

        def mock_evaluate_strategy_func(strategy_code_string, historical_data_path, strategy_config):
            call_number = len(eval_call_log)
            log_entry = f"DEBUG_EVAL_FUNC: Call {call_number + 1} for strategy '{strategy_code_string}'"
            print(log_entry) # Print to console
            eval_call_log.append(log_entry)

            if call_number < len(eval_responses):
                response = eval_responses[call_number]
                print(f"DEBUG_EVAL_FUNC: Returning response: {response}")
                return response
            else:
                error_msg = f"evaluate_strategy called {call_number + 1} times, but only {len(eval_responses)} responses were configured."
                print(f"DEBUG_EVAL_FUNC: ERROR - {error_msg}")
                raise AssertionError(error_msg)

        self.mock_fitness_evaluator.evaluate_strategy.side_effect = mock_evaluate_strategy_func
        
        try:
            best_code_empty_evolve, best_fitness_empty_evolve = self.generator.run_evolution()
        finally:
            # Restore original evolutionary engine
            self.generator.evolutionary_engine = original_evo_engine
        
        fresh_mock_evo_engine.initialize_population.assert_called_once_with(pop_size)
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, pop_size) # Only for the first generation
        
        expected_fitness_scores_passed_to_evolve = [fitness_s0_s2, fitness_s1_s2]
        fresh_mock_evo_engine.evolve_population.assert_called_once_with(initial_pop_s2, expected_fitness_scores_passed_to_evolve)
        
        # Best strategy should be from before population became empty
        expected_best_code_s2 = initial_pop_s2[0] 
        expected_best_fitness_s2 = fitness_s0_s2.copy()
        self.assertEqual(best_code_empty_evolve, expected_best_code_s2)
        self.assertEqual(best_fitness_empty_evolve, expected_best_fitness_s2)
        
        # Check for the log message
        self.mock_logger.error.assert_any_call("EvolutionaryEngine returned an empty population. Aborting.")


    def test_run_evolution_logging(self):
        self.mock_logger.reset_mock()
        num_generations = 2
        self.generator.config['num_generations'] = num_generations
        pop_size = self.config['population_size']
        primary_metric = self.mock_evolutionary_engine.primary_fitness_metric # e.g. 'sharpe_ratio'

        initial_pop = [f"init_s{i}" for i in range(pop_size)]
        evolved_pop_gen1 = [f"evolved_g1_s{i}" for i in range(pop_size)]

        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop
        self.mock_evolutionary_engine.evolve_population.side_effect = [evolved_pop_gen1]

        # Fitness scores: Gen0 (lower scores), Gen1 (higher scores, last one is best overall)
        fitness_scores_gen0 = [{primary_metric: 0.5 + i*0.05, 'id': f'g0_s{i}'} for i in range(pop_size)]
        fitness_scores_gen1 = [{primary_metric: 1.0 + i*0.1, 'id': f'g1_s{i}'} for i in range(pop_size)] # Gen1 has better scores
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = fitness_scores_gen0 + fitness_scores_gen1

        best_code, best_fitness = self.generator.run_evolution()
        
        # --- Assertions for logging ---
        self.mock_logger.info.assert_any_call(f"Starting evolution: {num_generations} generations, {pop_size} population size.")

        # Generation 1 (index 0 in loop, gen number is 1)
        self.mock_logger.info.assert_any_call(f"--- Generation {1}/{num_generations} ---")
        self.mock_logger.info.assert_any_call(f"Evaluating {len(initial_pop)} strategies...")
        best_fitness_gen0_value = fitness_scores_gen0[-1][primary_metric] 
        self.mock_logger.info.assert_any_call(f"Generation {1} best {primary_metric}: {best_fitness_gen0_value:.4f}")
        # The first generation's best will always be a "new overall best" initially if it's positive
        if best_fitness_gen0_value > -float('inf'):
             self.mock_logger.info.assert_any_call(f"New overall best strategy found in generation {1} with {primary_metric}: {best_fitness_gen0_value:.4f}")
        self.mock_logger.info.assert_any_call("Evolving population for next generation...")

        # Generation 2 (index 1 in loop, gen number is 2)
        self.mock_logger.info.assert_any_call(f"--- Generation {2}/{num_generations} ---")
        self.mock_logger.info.assert_any_call(f"Evaluating {len(evolved_pop_gen1)} strategies...")
        best_fitness_gen1_value = fitness_scores_gen1[-1][primary_metric]
        self.mock_logger.info.assert_any_call(f"Generation {2} best {primary_metric}: {best_fitness_gen1_value:.4f}")
        # Check if gen1's best is better than gen0's best
        if best_fitness_gen1_value > best_fitness_gen0_value:
            self.mock_logger.info.assert_any_call(f"New overall best strategy found in generation {2} with {primary_metric}: {best_fitness_gen1_value:.4f}")
        
        # For the last generation, "Evolving population for next generation..." is NOT called.
        # Instead, "Evolution finished." is called.
        self.mock_logger.info.assert_any_call("Evolution finished.")
        
        final_best_fitness_dict = fitness_scores_gen1[-1] 
        overall_best_val_for_log = final_best_fitness_dict.get(primary_metric, -float('inf'))
        self.mock_logger.info.assert_any_call(f"Best strategy overall ({primary_metric}: {overall_best_val_for_log:.4f}):")
        self.mock_logger.info.assert_any_call(f"Fitness Metrics: {final_best_fitness_dict}")
        
        self.assertEqual(best_code, evolved_pop_gen1[-1])
        self.assertEqual(best_fitness, final_best_fitness_dict)


    def test_run_evolution_llm_refinement_integration(self):
        # This test needs to be updated if LLM refinement is removed or changed in StrategyGenerator
        # For now, assuming num_llm_refinement_cycles is 0 by default or not used.
        # If StrategyGenerator.py re-enables LLM refinement, this test will need adjustment.
        self.generator.config['num_llm_refinement_cycles'] = 0 # Explicitly disable for this version of StrategyGenerator
        self.generator.config['num_generations'] = 1 
        pop_size = self.config['population_size']
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_llm_interface.reset_mock(); self.mock_logger.reset_mock()
        initial_pop = ["s_initial_best", "s_initial_other"]
        fitness_initial_best = {'sharpe_ratio': 1.5, 'id': 'initial_best_fit'}; fitness_initial_other = {'sharpe_ratio': 0.5, 'id': 'initial_other_fit'}
        # refined_code_from_llm = "refined_strategy_code"; fitness_refined = {'sharpe_ratio': 2.0, 'id': 'refined_fit'} # Not used if LLM cycles = 0
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [fitness_initial_best, fitness_initial_other] # Only initial evaluations
        # self.mock_llm_interface.refine_strategy_code.return_value = refined_code_from_llm # Not called
        
        best_code, best_fitness = self.generator.run_evolution()
        
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, pop_size) # No extra call for refinement
        self.mock_llm_interface.refine_strategy_code.assert_not_called() # LLM should not be called
        
        self.assertEqual(best_code, "s_initial_best") # Best from initial population
        expected_best_fitness = fitness_initial_best.copy() # Original fitness dict
        self.assertEqual(best_fitness, expected_best_fitness)
        
        # Check that no LLM refinement logging occurs
        for call_args in self.mock_logger.info.call_args_list:
            self.assertNotIn("LLM Refinement Cycle", call_args[0][0])


if __name__ == '__main__':
    unittest.main()
