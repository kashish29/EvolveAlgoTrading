import unittest
from algo_trading_framework.src.strategy_lab.llm_interface import MockLLMInterface

class TestMockLLMInterface(unittest.TestCase):

    def setUp(self):
        self.llm_interface = MockLLMInterface()

    def test_generate_strategy_code(self):
        prompt = "Create a simple RSI strategy."
        code = self.llm_interface.generate_strategy_code(prompt)
        self.assertIsInstance(code, str)
        self.assertTrue(len(code) > 50) # Expect some meaningful code string
        self.assertIn(prompt, code) # Mock includes prompt in output

    def test_mutate_strategy_code(self):
        initial_code = "class MyStrategy: pass"
        prompt = "Add a parameter for window size."
        mutated_code = self.llm_interface.mutate_strategy_code(initial_code, prompt)
        self.assertIsInstance(mutated_code, str)
        self.assertIn(initial_code, mutated_code) # Original code should be part of it
        # Mock LLM adds a comment that includes "mutated", let's check for that
        self.assertTrue("mutated" in mutated_code or "Mutated" in mutated_code or "# Code mutated" in mutated_code)


    def test_combine_strategy_codes(self):
        code_a = "class StrategyA: # Logic A"
        code_b = "class StrategyB: # Logic B"
        prompt = "Combine entry from A and exit from B."
        combined_code = self.llm_interface.combine_strategy_codes(code_a, code_b, prompt)
        self.assertIsInstance(combined_code, str)
        self.assertIn(code_a, combined_code)
        # The mock combine_strategy_codes might not include code_b directly in the top-level class it creates
        # but it should be mentioned in comments or be part of the string.
        self.assertIn("Strategy B", combined_code) # Check for mention of Strategy B
        self.assertIn("CombinedStrategy", combined_code) # Mock creates a combined class

if __name__ == '__main__':
    unittest.main()
