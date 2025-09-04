"""Configuration validation utilities."""

import os
import logging
from typing import List, Dict, Any
from app.config import settings


def validate_required_env_vars() -> List[str]:
    """Validate that all required environment variables are set."""
    required_vars = [
        "OPENAI_API_KEY",
        "TWILIO_ACCOUNT_SID", 
        "TWILIO_AUTH_TOKEN",
        "GOOGLE_CREDENTIALS_PATH",
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    return missing_vars


def validate_file_paths() -> List[str]:
    """Validate that required file paths exist."""
    file_paths = []
    
    if settings.GOOGLE_CREDENTIALS_PATH:
        if not os.path.exists(settings.GOOGLE_CREDENTIALS_PATH):
            file_paths.append(f"Google credentials file not found: {settings.GOOGLE_CREDENTIALS_PATH}")
    
    return file_paths


def validate_numeric_settings() -> List[str]:
    """Validate numeric configuration values."""
    issues = []
    
    if settings.CONFIRM_TTL_MIN <= 0:
        issues.append("CONFIRM_TTL_MIN must be positive")
    
    if settings.OPENAI_RATE_LIMIT_RPM <= 0:
        issues.append("OPENAI_RATE_LIMIT_RPM must be positive")
    
    if settings.OPENAI_RATE_LIMIT_TPM <= 0:
        issues.append("OPENAI_RATE_LIMIT_TPM must be positive")
    
    return issues


def validate_configuration() -> Dict[str, Any]:
    """Comprehensive configuration validation."""
    logger = logging.getLogger(__name__)
    
    validation_results = {
        "valid": True,
        "missing_env_vars": validate_required_env_vars(),
        "file_path_issues": validate_file_paths(),
        "numeric_issues": validate_numeric_settings(),
    }
    
    if any([
        validation_results["missing_env_vars"],
        validation_results["file_path_issues"], 
        validation_results["numeric_issues"]
    ]):
        validation_results["valid"] = False
        logger.error("Configuration validation failed")
        
        for missing_var in validation_results["missing_env_vars"]:
            logger.error("Missing required environment variable: %s", missing_var)
        
        for issue in validation_results["file_path_issues"]:
            logger.error("File path issue: %s", issue)
        
        for issue in validation_results["numeric_issues"]:
            logger.error("Numeric setting issue: %s", issue)
    else:
        logger.info("Configuration validation passed")
    
    return validation_results
