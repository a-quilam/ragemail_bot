"""
Output validation utilities for ensuring data integrity
"""
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of output validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_data: Optional[Any] = None


class OutputValidator:
    """Utility class for validating output data"""
    
    # Maximum lengths for different data types
    MAX_USERNAME_LENGTH = 32
    MAX_TEXT_LENGTH = 4096  # Telegram message limit
    MAX_CALLBACK_DATA_LENGTH = 64  # Telegram callback data limit
    MAX_USER_ID = 2**63 - 1  # Maximum Telegram user ID
    
    @staticmethod
    def validate_user_data(user_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate user data output
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        if not isinstance(user_data, dict):
            errors.append("User data must be a dictionary")
            return ValidationResult(False, errors, warnings)
        
        # Validate user ID
        user_id = user_data.get('id')
        if user_id is not None:
            if not isinstance(user_id, int):
                errors.append("User ID must be an integer")
            elif user_id <= 0 or user_id > OutputValidator.MAX_USER_ID:
                errors.append(f"User ID must be between 1 and {OutputValidator.MAX_USER_ID}")
        
        # Validate username
        username = user_data.get('username')
        if username is not None:
            if not isinstance(username, str):
                errors.append("Username must be a string")
            elif len(username) > OutputValidator.MAX_USERNAME_LENGTH:
                errors.append(f"Username too long (max {OutputValidator.MAX_USERNAME_LENGTH} characters)")
            elif not username.replace('_', '').isalnum():
                warnings.append("Username contains non-alphanumeric characters")
        
        # Validate role
        role = user_data.get('role')
        if role is not None:
            valid_roles = ['user', 'admin', 'superadmin']
            if role not in valid_roles:
                errors.append(f"Invalid role: {role}. Must be one of {valid_roles}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, user_data)
    
    @staticmethod
    def validate_mailbox_data(mailbox_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate mailbox data output
        
        Args:
            mailbox_data: Dictionary containing mailbox information
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        if not isinstance(mailbox_data, dict):
            errors.append("Mailbox data must be a dictionary")
            return ValidationResult(False, errors, warnings)
        
        # Validate mailbox ID
        mailbox_id = mailbox_data.get('id')
        if mailbox_id is not None:
            if not isinstance(mailbox_id, int):
                errors.append("Mailbox ID must be an integer")
            elif mailbox_id <= 0:
                errors.append("Mailbox ID must be positive")
        
        # Validate title
        title = mailbox_data.get('title')
        if title is not None:
            if not isinstance(title, str):
                errors.append("Title must be a string")
            elif len(title) > 100:  # Reasonable limit for mailbox title
                errors.append("Title too long (max 100 characters)")
            elif not title.strip():
                warnings.append("Title is empty or contains only whitespace")
        
        # Validate channel_id
        channel_id = mailbox_data.get('channel_id')
        if channel_id is not None:
            if not isinstance(channel_id, int):
                errors.append("Channel ID must be an integer")
            elif channel_id >= 0:
                errors.append("Channel ID must be negative (channels have negative IDs)")
        
        # Validate creator_id
        creator_id = mailbox_data.get('creator_id')
        if creator_id is not None:
            if not isinstance(creator_id, int):
                errors.append("Creator ID must be an integer")
            elif creator_id <= 0 or creator_id > OutputValidator.MAX_USER_ID:
                errors.append(f"Creator ID must be between 1 and {OutputValidator.MAX_USER_ID}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, mailbox_data)
    
    @staticmethod
    def validate_stats_data(stats_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate statistics data output
        
        Args:
            stats_data: Dictionary containing statistics information
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        if not isinstance(stats_data, dict):
            errors.append("Stats data must be a dictionary")
            return ValidationResult(False, errors, warnings)
        
        # Validate mailbox_id
        mailbox_id = stats_data.get('mailbox_id')
        if mailbox_id is not None:
            if not isinstance(mailbox_id, int):
                errors.append("Mailbox ID must be an integer")
            elif mailbox_id <= 0:
                errors.append("Mailbox ID must be positive")
        
        # Validate day
        day = stats_data.get('day')
        if day is not None:
            if not isinstance(day, str):
                errors.append("Day must be a string")
            elif len(day) != 10:  # Expected format: YYYY-MM-DD
                warnings.append("Day format might be incorrect (expected YYYY-MM-DD)")
        
        # Validate key
        key = stats_data.get('key')
        if key is not None:
            if not isinstance(key, str):
                errors.append("Key must be a string")
            elif len(key) > 50:  # Reasonable limit for stat key
                errors.append("Key too long (max 50 characters)")
        
        # Validate count
        count = stats_data.get('count')
        if count is not None:
            if not isinstance(count, int):
                errors.append("Count must be an integer")
            elif count < 0:
                errors.append("Count cannot be negative")
        
        return ValidationResult(len(errors) == 0, errors, warnings, stats_data)
    
    @staticmethod
    def validate_message_text(text: str) -> ValidationResult:
        """
        Validate message text output
        
        Args:
            text: Text to validate
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        if not isinstance(text, str):
            errors.append("Text must be a string")
            return ValidationResult(False, errors, warnings)
        
        # Check length
        if len(text) > OutputValidator.MAX_TEXT_LENGTH:
            errors.append(f"Text too long (max {OutputValidator.MAX_TEXT_LENGTH} characters)")
        
        # Check for empty text
        if not text.strip():
            warnings.append("Text is empty or contains only whitespace")
        
        # Check for potential HTML issues
        if '<' in text and '>' in text:
            # Basic check for unclosed tags
            open_tags = text.count('<')
            close_tags = text.count('>')
            if open_tags != close_tags:
                warnings.append("Potential HTML tag mismatch")
        
        # Check for excessive whitespace
        if '  ' in text:  # Multiple spaces
            warnings.append("Text contains multiple consecutive spaces")
        
        return ValidationResult(len(errors) == 0, errors, warnings, text)
    
    @staticmethod
    def validate_callback_data(callback_data: str) -> ValidationResult:
        """
        Validate callback data output
        
        Args:
            callback_data: Callback data to validate
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        if not isinstance(callback_data, str):
            errors.append("Callback data must be a string")
            return ValidationResult(False, errors, warnings)
        
        # Check length (Telegram limit is 64 bytes)
        byte_length = len(callback_data.encode('utf-8'))
        if byte_length > OutputValidator.MAX_CALLBACK_DATA_LENGTH:
            errors.append(f"Callback data too long ({byte_length} bytes, max {OutputValidator.MAX_CALLBACK_DATA_LENGTH})")
        
        # Check for invalid characters
        if not callback_data.replace('_', '').replace('-', '').isalnum():
            warnings.append("Callback data contains non-alphanumeric characters")
        
        return ValidationResult(len(errors) == 0, errors, warnings, callback_data)
    
    @staticmethod
    def validate_database_result(result: Any, expected_type: type = None) -> ValidationResult:
        """
        Validate database query result
        
        Args:
            result: Database query result
            expected_type: Expected type of the result
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        # Check if result is None
        if result is None:
            warnings.append("Database result is None")
            return ValidationResult(True, errors, warnings, result)
        
        # Check type if specified
        if expected_type and not isinstance(result, expected_type):
            errors.append(f"Expected {expected_type.__name__}, got {type(result).__name__}")
            return ValidationResult(False, errors, warnings)
        
        # For list results, check if empty
        if isinstance(result, list) and len(result) == 0:
            warnings.append("Database result is an empty list")
        
        # For dict results, check for required keys
        if isinstance(result, dict):
            if not result:
                warnings.append("Database result is an empty dictionary")
        
        return ValidationResult(len(errors) == 0, errors, warnings, result)
    
    @staticmethod
    def validate_api_response(response: Dict[str, Any]) -> ValidationResult:
        """
        Validate API response data
        
        Args:
            response: API response dictionary
            
        Returns:
            ValidationResult with validation status and any issues
        """
        errors = []
        warnings = []
        
        if not isinstance(response, dict):
            errors.append("API response must be a dictionary")
            return ValidationResult(False, errors, warnings)
        
        # Check for common API response fields
        if 'ok' in response:
            if not isinstance(response['ok'], bool):
                errors.append("API response 'ok' field must be boolean")
        
        if 'error_code' in response:
            if not isinstance(response['error_code'], int):
                errors.append("API response 'error_code' field must be integer")
        
        if 'description' in response:
            if not isinstance(response['description'], str):
                errors.append("API response 'description' field must be string")
        
        return ValidationResult(len(errors) == 0, errors, warnings, response)


def validate_message_text(text):
    """Simple message text validation function"""
    if not text:
        return ValidationResult(True, [], ["Text is empty"], "")
    if len(text) > 4096:
        return ValidationResult(False, ["Text too long"], [], text[:4096])
    return ValidationResult(True, [], [], text)

def validate_user_data(data):
    """Simple user data validation function"""
    if not data:
        return ValidationResult(True, [], ["User data is empty"], {})
    return ValidationResult(True, [], [], data)

def validate_output(data: Any, data_type: str = "generic") -> ValidationResult:
    """
    Convenience function for validating output data
    
    Args:
        data: Data to validate
        data_type: Type of data (user, mailbox, stats, message_text, callback_data, database_result, api_response)
        
    Returns:
        ValidationResult with validation status and any issues
    """
    if data_type == "user":
        return OutputValidator.validate_user_data(data)
    elif data_type == "mailbox":
        return OutputValidator.validate_mailbox_data(data)
    elif data_type == "stats":
        return OutputValidator.validate_stats_data(data)
    elif data_type == "message_text":
        return OutputValidator.validate_message_text(data)
    elif data_type == "callback_data":
        return OutputValidator.validate_callback_data(data)
    elif data_type == "database_result":
        return OutputValidator.validate_database_result(data)
    elif data_type == "api_response":
        return OutputValidator.validate_api_response(data)
    else:
        # Generic validation
        errors = []
        warnings = []
        
        if data is None:
            warnings.append("Data is None")
        elif isinstance(data, str) and not data.strip():
            warnings.append("String data is empty or whitespace only")
        elif isinstance(data, (list, dict)) and not data:
            warnings.append("Collection data is empty")
        
        return ValidationResult(True, errors, warnings, data)
