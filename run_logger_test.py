import logging
import os
from src.utils.logger import get_logger

def main():
    print("Starting logger test script...")

    # Create temporary directory for logs
    log_dir = "temp_test_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"Created directory: {log_dir}")

    log_file_path = os.path.join(log_dir, "test_app.log")
    print(f"Log file will be at: {log_file_path}")

    # Initialize loggers
    # Assuming get_logger parameters: name, level, log_file, log_to_console, log_to_file
    # (Adjust if the actual signature is different)
    
    print("\nInitializing logger_module_A (INFO level)...")
    logger_module_A = get_logger(
        logger_name="ModuleA",
        log_level=logging.INFO,
        log_file_path=log_file_path,
        log_to_console=True,
        log_to_file=True
    )

    print("Initializing logger_module_B (DEBUG level)...")
    logger_module_B = get_logger(
        logger_name="ModuleB",
        log_level=logging.DEBUG,
        log_file_path=log_file_path, # Both log to the same file
        log_to_console=True,
        log_to_file=True
    )

    print("\nLogging messages...")
    # Log messages
    logger_module_A.info("Info message from Module A")
    logger_module_A.debug("Debug message from Module A (should not appear in INFO level logger A's file/console output based on its level)")
    
    logger_module_B.info("Info message from Module B")
    logger_module_B.debug("Debug message from Module B (should appear in DEBUG level logger B's file/console output)")
    logger_module_B.error("Error message from Module B")

    print("\n--- Verification Instructions ---")
    print(f"Log file created at: {log_file_path}")
    print("Please manually verify the console output above and the log file for the following:")
    print("1. Correct formatting of messages (timestamp, logger name, level, message).")
    print("2. Presence of 'Info message from Module A' in both console and file.")
    print("3. ABSENCE of 'Debug message from Module A' in both console and file.")
    print("4. Presence of 'Info message from Module B' in both console and file.")
    print("5. Presence of 'Debug message from Module B' in both console and file.")
    print("6. Presence of 'Error message from Module B' in both console and file.")
    
    print("\nLogger test script finished.")

if __name__ == "__main__":
    # To ensure loggers are fresh if script is run multiple times in same python session (not applicable here)
    # logging.shutdown() 
    main()
