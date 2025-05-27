import yaml
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Loads a configuration file from the given YAML path.

    Args:
        config_path (str): The full path to the YAML configuration file.

    Returns:
        Dict[str, Any]: A dictionary containing the configuration.
                        Returns an empty dictionary if loading fails.
    Raises:
        FileNotFoundError: If the config file is not found.
        yaml.YAMLError: If there's an error parsing the YAML file.
    """
    try:
        with open(config_path, 'r') as stream:
            config = yaml.safe_load(stream)
            if config is None: # Handle empty YAML file case
                return {}
            print(f"Configuration loaded successfully from {config_path}")
            return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_path}")
        raise
    except yaml.YAMLError as exc:
        print(f"Error parsing YAML configuration file {config_path}: {exc}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while loading config {config_path}: {e}")
        raise # Or return {} depending on desired strictness

# Example usage:
if __name__ == '__main__':
    # Create a dummy config file for testing
    dummy_config_content = {
        "strategy_name": "MyAwesomeStrategy",
        "parameters": {
            "param1": 123,
            "param2": "value_abc"
        },
        "broker_settings": {
            "api_key": "YOUR_API_KEY",
            "secret": "YOUR_SECRET"
        }
    }
    dummy_path = "dummy_config.yaml"
    with open(dummy_path, 'w') as f:
        yaml.dump(dummy_config_content, f)

    try:
        loaded = load_config(dummy_path)
        print("\nLoaded config:")
        print(loaded)
        
        # Test non-existent file
        # load_config("non_existent_config.yaml")

        # Test invalid YAML
        # with open("invalid_dummy.yaml", "w") as f:
        #     f.write("strategy_name: MyStrategy\nparameters: param1: 10\n  param2: value2") # Incorrect indentation
        # load_config("invalid_dummy.yaml")

    except Exception as e:
        print(f"Example usage error: {e}")
