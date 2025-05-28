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
        self.mock_llm_interface = MockLLMInterface()
        
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
        
        self.default_fitness_score = {'sharpe_ratio': 1.0, 'total_return': 0.05, 'fitness_score': 1.0}
        self.mock_fitness_evaluator.evaluate_strategy.return_value = self.default_fitness_score
        
        # This attribute is accessed by StrategyGenerator, so it needs to be on the mock
        self.mock_evolutionary_engine.primary_fitness_metric = 'sharpe_ratio' 

        self.config = {
            'historical_data_path': 'dummy/path/to/data.csv',
            'strategy_config_template': {'symbol': 'TEST_SYM', 'param1': 10},
            'population_size': 2, 
            'num_generations': 3   # num_generations = 3 means 2 evolution steps
        }

        # Patch the logger for StrategyGenerator instances before instantiation
        self.logger_patcher = patch('src.strategy_lab.strategy_generator.logging.getLogger', return_value=MagicMock())
        self.mock_logger = self.logger_patcher.start()

        self.generator = StrategyGenerator(
            fitness_evaluator=self.mock_fitness_evaluator,
            evolutionary_engine=self.mock_evolutionary_engine,
            llm_interface=self.mock_llm_interface, 
            config=self.config
        )
        
    def tearDown(self):
        self.logger_patcher.stop()
        # No sys.modules cleanup needed as preamble is removed

    def test_run_evolution_basic_flow(self):
        """Test the basic flow of the run_evolution method."""
        pop_size = self.config['population_size']
        num_generations = self.config['num_generations']
        best_strategy_code, best_fitness = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        expected_eval_calls = pop_size * num_generations
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, expected_eval_calls)
        first_eval_call_args = self.mock_fitness_evaluator.evaluate_strategy.call_args_list[0]
        self.assertEqual(first_eval_call_args, call(
            self.initial_population[0], 
            self.config['historical_data_path'],
            self.config['strategy_config_template']
        ))
        self.assertEqual(self.mock_evolutionary_engine.evolve_population.call_count, num_generations -1)
        if num_generations > 1:
            first_evolve_call_args = self.mock_evolutionary_engine.evolve_population.call_args_list[0]
            expected_fitness_scores_with_code_key = []
            for i in range(pop_size):
                score = self.default_fitness_score.copy()
                score['code'] = self.initial_population[i]
                expected_fitness_scores_with_code_key.append(score)
            self.assertEqual(first_evolve_call_args, call(self.initial_population, expected_fitness_scores_with_code_key))
        expected_best_code = None
        if num_generations == 1: expected_best_code = self.initial_population[-1] 
        elif num_generations == 2: expected_best_code = self.evolved_population_gen1[-1] 
        elif num_generations == 3: expected_best_code = self.evolved_population_gen2[-1] 
        if expected_best_code:
            self.assertEqual(best_strategy_code, expected_best_code)
            expected_best_fitness = self.default_fitness_score.copy()
            expected_best_fitness['code'] = expected_best_code
            self.assertEqual(best_fitness, expected_best_fitness)
        else: 
             self.assertIsNone(best_strategy_code)
             self.assertIsNone(best_fitness)

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
        expected_best_fitness_with_code_key = expected_best_fitness_original.copy()
        expected_best_fitness_with_code_key['code'] = expected_best_code
        self.assertEqual(best_code, expected_best_code)
        self.assertEqual(best_fitness, expected_best_fitness_with_code_key)
        self.mock_evolutionary_engine.initialize_population.reset_mock(); self.mock_evolutionary_engine.evolve_population.reset_mock(); self.mock_fitness_evaluator.evaluate_strategy.reset_mock()
        f_g0i0_v2 = {'sharpe_ratio': 3.0, 'id': 'g0i0_v2'}; f_g0i1_v2 = {'sharpe_ratio': 1.0, 'id': 'g0i1_v2'}
        f_g1i0_v2 = {'sharpe_ratio': 1.2, 'id': 'g1i0_v2'}; f_g1i1_v2 = {'sharpe_ratio': 0.8, 'id': 'g1i1_v2'}
        f_g2i0_v2 = {'sharpe_ratio': 1.5, 'id': 'g2i0_v2'}; f_g2i1_v2 = {'sharpe_ratio': 1.3, 'id': 'g2i1_v2'}
        self.mock_evolutionary_engine.initialize_population.return_value = [s_g0i0, s_g0i1] 
        self.mock_evolutionary_engine.evolve_population.side_effect = [[s_g1i0, s_g1i1], [s_g2i0, s_g2i1]]
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [f_g0i0_v2, f_g0i1_v2, f_g1i0_v2, f_g1i1_v2, f_g2i0_v2, f_g2i1_v2]
        best_code_v2, best_fitness_v2 = self.generator.run_evolution()
        expected_best_code_v2 = s_g0i0; expected_best_fitness_original_v2 = f_g0i0_v2
        expected_best_fitness_with_code_key_v2 = expected_best_fitness_original_v2.copy()
        expected_best_fitness_with_code_key_v2['code'] = expected_best_code_v2
        self.assertEqual(best_code_v2, expected_best_code_v2)
        self.assertEqual(best_fitness_v2, expected_best_fitness_with_code_key_v2)

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
        expected_best_fitness_one_gen = fitness_g1_i0.copy(); expected_best_fitness_one_gen['code'] = expected_best_code_one_gen
        self.assertEqual(best_code_one_gen, expected_best_code_one_gen)
        self.assertEqual(best_fitness_one_gen, expected_best_fitness_one_gen)
        self.generator.config['num_generations'] = 0
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock()
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop_gen1_run 
        best_code_zero_gen, best_fitness_zero_gen = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.mock_fitness_evaluator.evaluate_strategy.assert_not_called()
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
        self.mock_logger.error.assert_any_call("Initial population is empty. Stopping evolution.")
        self.generator.config['num_generations'] = 2 
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_logger.reset_mock()
        initial_pop_s2 = ["s0_s2", "s1_s2"]
        fitness_s0_s2 = {'sharpe_ratio': 1.0, 'id': 's0_s2_fit'}; fitness_s1_s2 = {'sharpe_ratio': 0.5, 'id': 's1_s2_fit'}
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop_s2
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [fitness_s0_s2, fitness_s1_s2] 
        self.mock_evolutionary_engine.evolve_population.return_value = [] 
        best_code_empty_evolve, best_fitness_empty_evolve = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, pop_size)
        expected_fitness_scores_for_evolve = []
        for i in range(pop_size):
            score = [fitness_s0_s2, fitness_s1_s2][i].copy(); score['code'] = initial_pop_s2[i]
            expected_fitness_scores_for_evolve.append(score)
        self.mock_evolutionary_engine.evolve_population.assert_called_once_with(initial_pop_s2, expected_fitness_scores_for_evolve)
        expected_best_code_s2 = initial_pop_s2[0]; expected_best_fitness_s2 = fitness_s0_s2.copy()
        expected_best_fitness_s2['code'] = expected_best_code_s2
        self.assertEqual(best_code_empty_evolve, expected_best_code_s2)
        self.assertEqual(best_fitness_empty_evolve, expected_best_fitness_s2)
        self.mock_logger.warning.assert_any_call("Population became empty after evolution in generation 0. Stopping.")

    def test_run_evolution_logging(self):
        self.mock_logger.reset_mock() 
        num_generations = 2; self.generator.config['num_generations'] = num_generations
        pop_size = self.config['population_size']
        initial_pop = [f"init_s{i}" for i in range(pop_size)]; evolved_pop_gen1 = [f"evolved_g1_s{i}" for i in range(pop_size)]
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop
        self.mock_evolutionary_engine.evolve_population.side_effect = [evolved_pop_gen1] 
        fitness_scores_gen0 = [{'sharpe_ratio': 0.5 + i*0.1, 'id': f'g0_s{i}'} for i in range(pop_size)]
        fitness_scores_gen1 = [{'sharpe_ratio': 1.0 + i*0.1, 'id': f'g1_s{i}'} for i in range(pop_size)]
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = fitness_scores_gen0 + fitness_scores_gen1
        self.generator.run_evolution()
        self.mock_logger.info.assert_any_call("Starting evolution process...")
        for i in range(num_generations):
            self.mock_logger.info.assert_any_call(f"Generation {i}/{num_generations -1} evaluation complete.")
            current_pop_codes = []; current_fitness_results = []
            if i == 0: current_pop_codes = initial_pop; current_fitness_results = fitness_scores_gen0
            elif i == 1: current_pop_codes = evolved_pop_gen1; current_fitness_results = fitness_scores_gen1
            best_fitness_in_gen = None; best_code_in_gen = None; current_max_sharpe = -float('inf')
            for idx, fitness_dict in enumerate(current_fitness_results):
                if fitness_dict['sharpe_ratio'] > current_max_sharpe:
                    current_max_sharpe = fitness_dict['sharpe_ratio']; best_code_in_gen = current_pop_codes[idx] 
                    best_fitness_in_gen = fitness_dict.copy(); best_fitness_in_gen['code'] = best_code_in_gen 
            if best_fitness_in_gen: 
                 self.mock_logger.info.assert_any_call(f"Best strategy after generation {i}: {best_code_in_gen} with fitness: {best_fitness_in_gen}")
        self.mock_logger.info.assert_any_call("Evolution finished.")
        final_best_code = evolved_pop_gen1[-1] 
        final_best_fitness_dict = fitness_scores_gen1[-1].copy(); final_best_fitness_dict['code'] = final_best_code
        self.mock_logger.info.assert_any_call(f"Overall best strategy: {final_best_code} with fitness: {final_best_fitness_dict}")

    def test_run_evolution_llm_refinement_integration(self):
        self.generator.config['num_llm_refinement_cycles'] = 1; self.generator.config['num_generations'] = 1 
        pop_size = self.config['population_size']
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_llm_interface.reset_mock(); self.mock_logger.reset_mock()
        initial_pop = ["s_initial_best", "s_initial_other"]
        fitness_initial_best = {'sharpe_ratio': 1.5, 'id': 'initial_best_fit'}; fitness_initial_other = {'sharpe_ratio': 0.5, 'id': 'initial_other_fit'}
        refined_code_from_llm = "refined_strategy_code"; fitness_refined = {'sharpe_ratio': 2.0, 'id': 'refined_fit'} 
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [fitness_initial_best, fitness_initial_other, fitness_refined]
        self.mock_llm_interface.refine_strategy_code.return_value = refined_code_from_llm
        best_code, best_fitness = self.generator.run_evolution()
        self.mock_evolutionary_engine.initialize_population.assert_called_once_with(pop_size)
        self.assertEqual(self.mock_fitness_evaluator.evaluate_strategy.call_count, pop_size + 1) 
        expected_feedback_prompt = ("This strategy has a Sharpe Ratio of 1.5. Refine it to improve its performance, focusing on the Sharpe Ratio. Original code:\n\ns_initial_best")
        self.mock_llm_interface.refine_strategy_code.assert_called_once_with("s_initial_best", expected_feedback_prompt)
        self.assertEqual(best_code, refined_code_from_llm)
        expected_best_fitness = fitness_refined.copy(); expected_best_fitness['code'] = refined_code_from_llm
        self.assertEqual(best_fitness, expected_best_fitness)
        self.mock_logger.info.assert_any_call(f"LLM Refinement Cycle 1/1: Best strategy after refinement: {refined_code_from_llm} with fitness: {expected_best_fitness}")
        self.generator.config['num_llm_refinement_cycles'] = 1
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_llm_interface.reset_mock()
        fitness_refined_worse = {'sharpe_ratio': 1.0, 'id': 'refined_worse_fit'} 
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [fitness_initial_best, fitness_initial_other, fitness_refined_worse]
        self.mock_llm_interface.refine_strategy_code.return_value = refined_code_from_llm 
        best_code_worse, best_fitness_worse = self.generator.run_evolution()
        self.assertEqual(best_code_worse, "s_initial_best") 
        expected_best_fitness_worse = fitness_initial_best.copy(); expected_best_fitness_worse['code'] = "s_initial_best"
        self.assertEqual(best_fitness_worse, expected_best_fitness_worse)
        self.generator.config['num_llm_refinement_cycles'] = 0
        self.mock_evolutionary_engine.reset_mock(); self.mock_fitness_evaluator.reset_mock(); self.mock_llm_interface.reset_mock()
        self.mock_evolutionary_engine.initialize_population.return_value = initial_pop
        self.mock_fitness_evaluator.evaluate_strategy.side_effect = [fitness_initial_best, fitness_initial_other]
        best_code_no_llm, best_fitness_no_llm = self.generator.run_evolution()
        self.mock_llm_interface.refine_strategy_code.assert_not_called()
        self.assertEqual(best_code_no_llm, "s_initial_best") 
        expected_best_fitness_no_llm = fitness_initial_best.copy(); expected_best_fitness_no_llm['code'] = "s_initial_best"
        self.assertEqual(best_fitness_no_llm, expected_best_fitness_no_llm)

if __name__ == '__main__':
    unittest.main()
