import unittest
from algo_trading_framework.src.strategy_lab.strategy_generator import StrategyGenerator
from algo_trading_framework.src.strategy_lab.llm_interface import MockLLMInterface
from algo_trading_framework.src.strategy_lab.fitness_evaluator import MockFitnessEvaluator
from algo_trading_framework.src.strategy_lab.evolutionary_engine import MockEvolutionaryEngine

class TestStrategyGenerator(unittest.TestCase):

    def setUp(self):
        self.llm_mock = MockLLMInterface()
        self.fitness_mock = MockFitnessEvaluator()
        self.evo_mock = MockEvolutionaryEngine(llm_interface=self.llm_mock)
        self.generator = StrategyGenerator(
            llm_interface=self.llm_mock,
            fitness_evaluator=self.fitness_mock,
            evolutionary_engine=self.evo_mock,
            population_size=3
        )

    def test_generate_initial_population(self):
        self.assertEqual(len(self.generator.current_population_codes), 0)
        self.generator.generate_initial_population(num_strategies=2)
        self.assertEqual(len(self.generator.current_population_codes), 2)
        self.assertEqual(len(self.generator.current_fitness_scores), 2)
        for code in self.generator.current_population_codes:
            self.assertIsInstance(code, str)
            self.assertTrue(len(code) > 0)
        for score in self.generator.current_fitness_scores:
            self.assertIsInstance(score, float)

    def test_run_evolution_cycle(self):
        self.generator.generate_initial_population(num_strategies=3)
        initial_pop_codes = list(self.generator.current_population_codes)
        
        self.generator.run_evolution_cycle(num_generations=1)
        
        self.assertEqual(len(self.generator.current_population_codes), 3)
        self.assertEqual(len(self.generator.current_fitness_scores), 3)
        # Check if population codes have changed (mock evolution adds a comment)
        # This depends on the mock evolutionary engine's behavior
        # For example, if run_evolution_step returns modified codes:
        # self.assertNotEqual(initial_pop_codes[0], self.generator.current_population_codes[0])
        # The current MockEvolutionaryEngine's run_evolution_step does modify them.
        
        # A simple check to see if the code has been 'touched' by the mock evolutionary process.
        # This assumes the mock evolutionary engine adds identifiable markers (like comments).
        if initial_pop_codes and self.generator.current_population_codes:
             # Not all codes might change due to elitism or other factors in a real engine.
             # For this mock, most should change.
             changed_count = 0
             for i_code, n_code in zip(initial_pop_codes, self.generator.current_population_codes):
                 if i_code != n_code: # Check if string content is different
                     changed_count+=1
             self.assertTrue(changed_count > 0 or len(initial_pop_codes) == 0, "At least one strategy code should have been modified by the mock evolution.")


    def test_get_best_strategy(self):
        self.generator.generate_initial_population(num_strategies=3)
        # Manually set fitness scores for predictability if needed, or rely on mock
        # For this test, we rely on the mock fitness evaluator and check structure
        # Ensure there are fitness scores:
        if not self.generator.current_fitness_scores: # Should be populated by generate_initial_population
            self.fail("Fitness scores not populated after generating initial population.")

        best_strat_info = self.generator.get_best_strategy()
        self.assertIsNotNone(best_strat_info)
        if best_strat_info:
            code, fitness = best_strat_info
            self.assertIsInstance(code, str)
            self.assertIsInstance(fitness, float)
            self.assertEqual(fitness, max(self.generator.current_fitness_scores))

if __name__ == '__main__':
    unittest.main()
