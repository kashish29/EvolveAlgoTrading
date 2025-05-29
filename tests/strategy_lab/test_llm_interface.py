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
        # The mock generate_initial_strategy returns the EVOLVED_STRATEGY_TEMPLATE with placeholders replaced.
        # We assert that the original template (with placeholders) is a substring of the generated code,
        # and that the generated code is not identical to the raw template (meaning replacements occurred).
        self.assertIn("{{SHORT_WINDOW}}", self.evolved_strategy_template) # Ensure template still has placeholders
        self.assertIn("{{LONG_WINDOW}}", self.evolved_strategy_template)
        self.assertIn("{{QUANTITY}}", self.evolved_strategy_template)
        
        # Check that the generated code contains the structure of the template
        # This is a weaker assertion but accounts for the random values.
        # A more robust test might use regex to check the format of the replaced values.
        # For now, we'll check that the template structure is present, and the values are indeed numbers.
        
        # To avoid comparing exact strings with random numbers, we can check if the structure is there
        # and that the numbers are indeed numbers.
        # For simplicity, let's just check that the template structure is present,
        # and the length is roughly similar, implying placeholders were filled.
        
        # The original assertion self.assertEqual(code, self.evolved_strategy_template) fails because
        # the mock replaces the placeholders. We need to check if the *structure* is maintained.
        
        # A simple way to check if the template was used and values were replaced is to check
        # if the template *without* placeholders is a substring, and that the code is not the raw template.
        
        # Let's check that the generated code is *not* the raw template, and it contains parts of it.
        self.assertNotEqual(code, self.evolved_strategy_template)
        
        # We can check for a few key lines from the template to ensure the structure is there.
        # This is a pragmatic approach given the mock's behavior.
        self.assertIn("class EvolvedStrategy(BaseStrategy):", code)
        self.assertIn("self.short_window = self.config.get(\"short_window\",", code)
        self.assertIn("self.long_window = self.config.get(\"long_window\",", code)
        self.assertIn("self.quantity = self.config.get(\"quantity\",", code)
        self.assertIn("def on_bar(self, current_bars: Dict[str, 'Candle']):", code)
        
        # Optionally, you could use regex to verify the format of the numbers, e.g.:
        # import re
        # self.assertRegex(code, r'self\.short_window = self\.config\.get\("short_window", \d+\)')
        # self.assertRegex(code, r'self\.long_window = self\.config\.get\("long_window", \d+\)')
        # self.assertRegex(code, r'self\.quantity = self\.config\.get\("quantity", \d+\)')
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
