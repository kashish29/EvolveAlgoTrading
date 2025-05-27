import unittest
from algo_trading_framework.src.strategy_lab.fitness_evaluator import MockFitnessEvaluator

class TestMockFitnessEvaluator(unittest.TestCase):

    def setUp(self):
        self.evaluator = MockFitnessEvaluator()

    def test_evaluate_strategy(self):
        strategy_code = "class TestStrategy: def on_bar(self): return 'BUY'"
        fitness = self.evaluator.evaluate_strategy(strategy_code, "test_strat_01")
        self.assertIsInstance(fitness, float)
        # Mock fitness can be anything, just check type

if __name__ == '__main__':
    unittest.main()
