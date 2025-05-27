from typing import List, Dict, Any, Optional
import random

try:
    from .llm_interface import MockLLMInterface
    from .fitness_evaluator import MockFitnessEvaluator
    from .evolutionary_engine import MockEvolutionaryEngine
except ImportError:
    # Dummy classes for standalone execution
    class MockLLMInterface: 
        def generate_strategy_code(self,p,t=None): return f"# Mock LLM Code for {p}"
    class MockFitnessEvaluator:
        def evaluate_strategy(self,c, sid=None): return random.uniform(0,100)
    class MockEvolutionaryEngine:
        def __init__(self, llm_interface): pass
        def run_evolution_step(self, pop, fits): return [p + "\n# Evolved" for p in pop]

class StrategyGenerator:
    """
    Orchestrates the AI-driven strategy generation process.
    It uses an LLM interface to create initial strategies, an evolutionary engine
    to evolve them, and a fitness evaluator to assess their performance.
    """
    def __init__(self, llm_interface: MockLLMInterface, 
                 fitness_evaluator: MockFitnessEvaluator, 
                 evolutionary_engine: MockEvolutionaryEngine,
                 population_size: int = 10): # Small default population for mock
        self.llm_interface = llm_interface
        self.fitness_evaluator = fitness_evaluator
        self.evolutionary_engine = evolutionary_engine
        self.population_size = population_size
        self.current_population_codes: List[str] = []
        self.current_fitness_scores: List[float] = []
        print("StrategyGenerator initialized.")

    def generate_initial_population(self, num_strategies: Optional[int] = None, base_prompt: str = "Create a trading strategy."):
        """
        Generates an initial population of strategies using the LLM interface.
        Args:
            num_strategies (int, optional): Number of strategies to generate. Defaults to self.population_size.
            base_prompt (str): A base prompt for the LLM. Can be made more specific.
        """
        if num_strategies is None:
            num_strategies = self.population_size
            
        print(f"StrategyGenerator: Generating initial population of {num_strategies} strategies...")
        self.current_population_codes = []
        for i in range(num_strategies):
            # Vary prompts slightly for diversity if desired
            prompt = f"{base_prompt} (Variation {i+1})"
            strategy_code = self.llm_interface.generate_strategy_code(prompt)
            self.current_population_codes.append(strategy_code)
            print(f"  Generated strategy {i+1} (code length: {len(strategy_code)}).")
        
        # Evaluate this initial population
        self._evaluate_current_population()

    def _evaluate_current_population(self):
        """Evaluates all strategies in the current population and stores their fitness scores."""
        print("StrategyGenerator: Evaluating current population...")
        self.current_fitness_scores = []
        for i, strategy_code in enumerate(self.current_population_codes):
            fitness = self.fitness_evaluator.evaluate_strategy(strategy_code, strategy_id=f"gen_pop_strat_{i}")
            self.current_fitness_scores.append(fitness)
        print("StrategyGenerator: Population evaluation complete.")

    def run_evolution_cycle(self, num_generations: int = 3): # Few generations for mock
        """
        Runs the evolutionary process for a specified number of generations.
        Args:
            num_generations (int): The number of generations to evolve.
        """
        if not self.current_population_codes:
            print("StrategyGenerator: Initial population not generated. Please call generate_initial_population() first.")
            self.generate_initial_population() # Auto-generate if not present

        print(f"StrategyGenerator: Starting evolution cycle for {num_generations} generations...")
        for gen in range(num_generations):
            print(f"\n--- Generation {gen + 1} ---")
            if not self.current_population_codes or not self.current_fitness_scores or \
               len(self.current_population_codes) != len(self.current_fitness_scores):
                print("Error: Population and fitness scores are misaligned or empty. Re-evaluating.")
                self._evaluate_current_population()
                if not self.current_population_codes: # Still no population
                    print("Critical Error: No population to evolve. Aborting cycle.")
                    return

            new_population_codes = self.evolutionary_engine.run_evolution_step(
                self.current_population_codes,
                self.current_fitness_scores
            )
            self.current_population_codes = new_population_codes
            self._evaluate_current_population() # Evaluate the new generation

            # Log best fitness in this generation (optional)
            if self.current_fitness_scores:
                best_fitness_this_gen = max(self.current_fitness_scores)
                avg_fitness_this_gen = sum(self.current_fitness_scores) / len(self.current_fitness_scores)
                print(f"Generation {gen+1} Summary: Best Fitness = {best_fitness_this_gen:.2f}, Avg Fitness = {avg_fitness_this_gen:.2f}")
        
        print("\nStrategyGenerator: Evolution cycle finished.")

    def get_best_strategy(self) -> Optional[Tuple[str, float]]:
        """
        Returns the strategy code and fitness score of the best individual
        in the current population.
        """
        if not self.current_population_codes or not self.current_fitness_scores:
            print("StrategyGenerator: No population or fitness scores available to determine best strategy.")
            return None
        
        best_idx = self.current_fitness_scores.index(max(self.current_fitness_scores))
        return self.current_population_codes[best_idx], self.current_fitness_scores[best_idx]

# Example Usage
if __name__ == '__main__':
    llm_iface = MockLLMInterface()
    fitness_eval = MockFitnessEvaluator()
    evo_engine = MockEvolutionaryEngine(llm_interface=llm_iface) # Pass LLM if engine uses it
    
    generator = StrategyGenerator(llm_iface, fitness_eval, evo_engine, population_size=5)
    
    # Generate initial population (will also evaluate it)
    generator.generate_initial_population(base_prompt="Design a mean-reversion strategy for forex markets")
    
    # Run a few generations of evolution
    generator.run_evolution_cycle(num_generations=2)
    
    # Get the best strategy found
    best_strat_info = generator.get_best_strategy()
    if best_strat_info:
        best_code, best_fitness = best_strat_info
        print(f"\n--- Best Strategy Found (Fitness: {best_fitness:.2f}) ---")
        print(best_code[:300] + "\n...") # Print snippet
    else:
        print("\nNo best strategy could be determined.")

```
