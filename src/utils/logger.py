import logging
import sys
from typing import Optional

DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def get_logger(name: str, 
               log_level: int = logging.INFO, 
               log_format: str = DEFAULT_LOG_FORMAT,
               date_format: str = DEFAULT_DATE_FORMAT,
               log_to_console: bool = True,
               log_file: Optional[str] = None):
    """
    Configures and returns a logger instance.

    Args:
        name (str): The name for the logger (e.g., __name__ of the calling module).
        log_level (int): The logging level (e.g., logging.INFO, logging.DEBUG).
        log_format (str): The format string for log messages.
        date_format (str): The format string for dates in log messages.
        log_to_console (bool): If True, logs to the console.
        log_file (str, optional): Path to a file to log to. If None, no file logging.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Prevent multiple handlers if logger already configured (e.g., in interactive sessions)
    if logger.hasHandlers():
        # Optionally, clear existing handlers if you want to reconfigure:
        # logger.handlers.clear()
        # For now, just return the existing logger if it's already set up to avoid duplication.
        # However, ensure its level is at least as verbose as requested.
        if logger.level > log_level : # logger.level is 0 if not set, so this works if it was never set
             logger.setLevel(log_level)
        # This basic check doesn't guarantee the handlers are what we want.
        # A more robust setup for libraries might involve a central configuration point.
        # For this framework, let's assume we want to add handlers if none match our criteria.
        # Or, simply, if we call get_logger multiple times, we might get multiple console outputs.
        # A common pattern is to configure the root logger once, or use a flag.
        # For simplicity here, we'll add handlers each time, which can lead to duplicate logs if called carelessly.
        # A better approach for a library: configure only if no handlers exist.
        
        # Let's refine: only add new handlers if no similar handlers exist.
        # This is still imperfect but better than always adding.
        # For this project, let's keep it simple: if called multiple times for same name, it might get multiple handlers.
        pass # Fall through to add handlers, be mindful of calling this.

    logger.setLevel(log_level)
    formatter = logging.Formatter(log_format, datefmt=date_format)

    if log_to_console:
        # Check if a similar console handler already exists
        if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in logger.handlers):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

    if log_file:
        # Check if a similar file handler already exists
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_file for h in logger.handlers):
            try:
                file_handler = logging.FileHandler(log_file, mode='a') # Append mode
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.error(f"Failed to attach file handler for {log_file}: {e}", exc_info=True)
                
    # If no handlers were added (e.g. console=False, log_file=None, and no pre-existing)
    # add a default NullHandler to prevent "No handlers could be found" warnings for library use.
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())


    return logger

# Example Usage:
if __name__ == '__main__':
    # Basic console logger
    logger1 = get_logger("MyModuleLogger")
    logger1.info("This is an info message from logger1.")
    logger1.debug("This is a debug message from logger1 (should not appear by default).")

    # Logger with debug level and output to a file
    # Ensure 'logs' directory exists if you run this directly, or specify full path.
    # For framework, logs dir should be created by main script or deployment.
    import os
    log_dir = "temp_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger2 = get_logger("FileLogger", log_level=logging.DEBUG, log_file=os.path.join(log_dir, "app.log"))
    logger2.debug("This is a debug message to console and file from logger2.")
    logger2.info("This is an info message to console and file from logger2.")
    logger2.warning("A warning from logger2.")
    logger2.error("An error from logger2.")
    
    # Test calling get_logger again for the same name - check for duplicate console logs
    logger1_again = get_logger("MyModuleLogger")
    logger1_again.info("Info message from logger1_again. If duplicated, handler logic needs refinement.")
    # The current simple implementation might add another console handler.
    # For a production app, logger configuration is often done once at startup.
    
    print(f"Log file created at: {os.path.join(log_dir, 'app.log')} (if file logging was successful)")
