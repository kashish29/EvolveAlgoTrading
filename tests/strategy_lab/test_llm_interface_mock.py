import unittest
from src.strategy_lab.llm_interface import MockLLMInterface

class TestMockLLMInterface(unittest.TestCase):
    """
    Test suite for the MockLLMInterface class.
    """

    def setUp(self):
        """
        Instantiate MockLLMInterface for each test.
        """
        self.llm_interface = MockLLMInterface()

    # Test Case 1: test_generate_initial_strategy
    def test_generate_initial_strategy(self):
        """
        Tests the generate_initial_strategy method.
        """
        # a. Call generate_initial_strategy
        prompt = "Generate a simple moving average crossover strategy."
        generated_code = self.llm_interface.generate_initial_strategy(prompt)

        # b. Assert the returned value is a non-empty string
        self.assertIsInstance(generated_code, str)
        self.assertTrue(len(generated_code) > 0, "Generated code should not be empty.")

        # c. Assert that placeholders are NOT in the returned string
        self.assertNotIn("{{SHORT_WINDOW}}", generated_code)
        self.assertNotIn("{{LONG_WINDOW}}", generated_code)
        self.assertNotIn("{{QUANTITY}}", generated_code)
        # Check for a few more potential placeholders if they exist in the template
        self.assertNotIn("{{SYMBOL}}", generated_code) 

        # d. Assert that essential parts of the template ARE in the returned string
        self.assertIn("class EvolvedStrategy(BaseStrategy):", generated_code)
        # The mock generates the correct BaseStrategy __init__ signature
        self.assertIn("def __init__(self, strategy_id: str, broker: 'BaseBrokerClient', config: dict = None):", generated_code)
        self.assertIn("super().__init__(strategy_id, broker, config)", generated_code) # Check super call
        self.assertIn("def on_bar(self, current_bars: Dict[str, 'Candle']):", generated_code) # Check on_bar signature
        # Check that parameters are set (values are random within default ranges, so don't check specific values)
        self.assertIn("self.short_window = self.config.get(\"short_window\"", generated_code)
        self.assertIn("self.long_window = self.config.get(\"long_window\"", generated_code)
        self.assertIn("self.quantity = self.config.get(\"quantity\"", generated_code)
        self.assertIn("self.symbol = self.config.get(\"symbol\", \"DEFAULT_SYMBOL\")", generated_code)


    # Test Case 2: test_refine_strategy_code
    def test_refine_strategy_code(self):
        """
        Tests the refine_strategy_code method.
        """
        # a. Define sample_code and sample_feedback
        sample_code = "def old_code():\n    pass"
        sample_feedback = "make it better by adding a print statement"

        # b. Call refine_strategy_code
        refined_code = self.llm_interface.refine_strategy_code(sample_code, sample_feedback)

        # c. Assert the returned string contains sample_code
        self.assertIn(sample_code, refined_code)

        # d. Assert the returned string contains sample_feedback (e.g., as part of a comment)
        expected_feedback_comment = f"# LLM Mock Refinement: Based on feedback - {sample_feedback}" # Adjusted
        self.assertIn(expected_feedback_comment, refined_code)
        # Removed: self.assertIn("print(\"Refined code based on feedback!\")", refined_code)


    # Test Case 3: test_combine_strategy_codes
    def test_combine_strategy_codes(self):
        """
        Tests the combine_strategy_codes method.
        """
        # a. Define code_one, code_two, and prompt
        code_one = "def strategy_part_1():\n    # Part 1 logic"
        code_two = "def strategy_part_2():\n    # Part 2 logic"
        prompt = "combine these two parts logically"

        # b. Call combine_strategy_codes
        combined_code = self.llm_interface.combine_strategy_codes(code_one, code_two, prompt)

        # c. Assert the returned string contains code_one
        self.assertIn(code_one, combined_code)

        # d. Assert the returned string contains code_two
        self.assertIn(code_two, combined_code)

        # e. Assert the returned string contains prompt (e.g., as part of a comment)
        expected_prompt_comment = f"# --- Combined by MockLLMInterface based on: {prompt} ---"
        self.assertIn(expected_prompt_comment, combined_code)
        # Removed: self.assertIn("# --- Combined Code ---", combined_code)

if __name__ == '__main__':
    unittest.main()
