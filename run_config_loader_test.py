import yaml
import os

# Adjust the import path if necessary based on how you run the script
# If running from the root of the project:
from src.utils.config_loader import load_config

def main():
    print("Starting config loader test script...")
    successful_loads = 0

    # --- Load example_strategy.yaml ---
    example_strategy_path = "config/strategy_params/example_strategy.yaml"
    print(f"\nAttempting to load: {example_strategy_path}")
    try:
        strategy_config = load_config(example_strategy_path)
        if strategy_config:
            print("Successfully loaded example_strategy.yaml:")
            print(yaml.dump(strategy_config, indent=2))
            successful_loads += 1
        else:
            # This case should ideally be handled by load_config raising an error
            print("Failed to load example_strategy.yaml, no content returned.")
    except FileNotFoundError:
        print(f"Error: File not found at {example_strategy_path}")
    except yaml.YAMLError as e:
        print(f"Error: YAML parsing error in {example_strategy_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while loading {example_strategy_path}: {e}")

    # --- Load mock_main_config.yaml ---
    mock_main_config_path = "config/mock_main_config.yaml"
    print(f"\nAttempting to load: {mock_main_config_path}")
    try:
        main_config = load_config(mock_main_config_path)
        if main_config:
            print("Successfully loaded mock_main_config.yaml:")
            print(yaml.dump(main_config, indent=2))
            successful_loads += 1
        else:
            # This case should ideally be handled by load_config raising an error
            print("Failed to load mock_main_config.yaml, no content returned.")
    except FileNotFoundError:
        print(f"Error: File not found at {mock_main_config_path}")
    except yaml.YAMLError as e:
        print(f"Error: YAML parsing error in {mock_main_config_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while loading {mock_main_config_path}: {e}")

    # --- Report success ---
    print("\n--- Summary ---")
    if successful_loads == 2:
        print("Successfully loaded and displayed both example_strategy.yaml and mock_main_config.yaml.")
    else:
        print(f"Failed to load one or more configuration files. Successfully loaded {successful_loads} file(s).")
    
    print("\nConfig loader test script finished.")

if __name__ == "__main__":
    main()
