import unittest
from unittest.mock import MagicMock 
from src.strategy_lab.llm_interface import MockLLMInterface, EVOLVED_STRATEGY_TEMPLATE # Import template for comparison

class TestMockLLMInterface(unittest.TestCase):

    def setUp(self):
        self.llm_interface = MockLLMInterface()
        self.evolved_strategy_template = EVOLVED_STRATEGY_TEMPLATE

    def test_generate_initial_strategy(self): # Renamed test method
        prompt = "Create a simple RSI strategy."
        code = self.llm_interface.generate_initial_strategy(prompt) # Calls existing method
        self.assertIsInstance(code, str)
        self.assertTrue(len(code) > 50) 
        # The mock generate_initial_strategy returns the EVOLVED_STRATEGY_TEMPLATE
        self.assertEqual(code, self.evolved_strategy_template)
        # The print statement in the mock includes the prompt, but the return value does not.
        # If we wanted to check the prompt interaction, we'd need to capture stdout or have the mock return it.

    def test_refine_strategy_code(self): # Renamed test method
        initial_code = "class MyStrategy: pass"
        feedback = "Add a parameter for window size."
        refined_code = self.llm_interface.refine_strategy_code(initial_code, feedback) # Calls existing method
        self.assertIsInstance(refined_code, str)
        self.assertIn(initial_code, refined_code) 
        # Mock refine_strategy_code appends a comment with the feedback.
        expected_refinement_comment = f"# LLM Mock Refinement: Based on feedback - {feedback}"
        self.assertIn(expected_refinement_comment, refined_code)


    def test_combine_strategy_codes(self):
        code_a = "class StrategyA: # Logic A"
        code_b = "class StrategyB: # Logic B"
        prompt = "Combine entry from A and exit from B."
        combined_code = self.llm_interface.combine_strategy_codes(code_a, code_b, prompt)
        self.assertIsInstance(combined_code, str)
        self.assertIn(code_a, combined_code)
        self.assertIn(code_b, combined_code) # Mock concatenates them
        # Mock combine_strategy_codes includes the prompt in a comment.
        expected_combination_comment = f"# --- Combined by MockLLMInterface based on: {prompt} ---"
        self.assertIn(expected_combination_comment, combined_code)

if __name__ == '__main__':
    unittest.main()
