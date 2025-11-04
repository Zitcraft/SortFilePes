#!/usr/bin/env python3
"""
Workflow Logger Library
Provides logging functionality for the embroidery management workflow.
"""

import logging
import sys
from datetime import datetime

# Add custom USERINPUT log level
USERINPUT_LEVEL = 25  # Between INFO (20) and WARNING (30)
logging.addLevelName(USERINPUT_LEVEL, 'USER')


class WorkflowLogger:
    """Centralized logger for the embroidery workflow."""
    
    def __init__(self, log_file="workflow_log.txt", logger_name='workflow'):
        self.log_file = log_file
        self.logger_name = logger_name
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging to both console and file."""
        # Create logger
        logger = logging.getLogger(self.logger_name)
        logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Create formatters
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        
        # File handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_print(self, message):
        """Print and log message."""
        self.logger.info(message)
    
    def log_debug(self, message):
        """Log debug message."""
        self.logger.debug(message)
    
    def log_warning(self, message):
        """Log warning message."""
        self.logger.warning(message)
    
    def log_error(self, message):
        """Log error message."""
        self.logger.error(message)
    
    def log_userinput(self, message):
        """Log user input with custom level."""
        self.logger.log(USERINPUT_LEVEL, message)
    
    def logged_input(self, prompt):
        """Get user input and log it."""
        try:
            self.logger.info(prompt)
            user_input = input("╰┈➤ ")
            if user_input == "":
                self.log_userinput(f"-> Enter")
            else:
                self.log_userinput(f"-> {user_input}")

            return user_input
        except (KeyboardInterrupt, EOFError) as e:
            self.logger.info(f"User input interrupted: {e}")
            raise


# Global logger instance for convenience
_global_logger = None


def get_logger(log_file="workflow_log.txt", logger_name='workflow'):
    """Get or create global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = WorkflowLogger(log_file, logger_name)
    return _global_logger


def setup_logging(log_file="workflow_log.txt", logger_name='workflow'):
    """Setup logging and return logger instance (for backward compatibility)."""
    return get_logger(log_file, logger_name).logger


def log_print(message):
    """Print and log message using global logger."""
    get_logger().log_print(message)


def log_debug(message):
    """Log debug message using global logger."""
    get_logger().log_debug(message)


def log_warning(message):
    """Log warning message using global logger."""
    get_logger().log_warning(message)


def log_error(message):
    """Log error message using global logger."""
    get_logger().log_error(message)


def log_userinput(message):
    """Log user input using global logger."""
    get_logger().log_userinput(message)


def logged_input(prompt):
    """Get user input and log it using global logger."""
    return get_logger().logged_input(prompt)


# For backward compatibility
def setup_logging_legacy():
    """Legacy setup function that returns the logger object."""
    logger_instance = get_logger()
    return logger_instance.logger
