"""
Input sanitization utilities for user data
"""
import re
import html
import logging
from typing import Optional, Union


class InputSanitizer:
    """Utility class for sanitizing user input"""
    
    # Regex patterns for validation
    USERNAME_PATTERN = re.compile(r'^@?[a-zA-Z0-9_]{5,32}$')
    USER_ID_PATTERN = re.compile(r'^\d{1,10}$')
    TEXT_PATTERN = re.compile(r'^[a-zA-Zа-яА-Я0-9\s@_.,!?\-()]+$')
    
    # Maximum lengths
    MAX_USERNAME_LENGTH = 32
    MAX_TEXT_LENGTH = 1000
    MAX_USER_ID_LENGTH = 10
    
    @staticmethod
    def sanitize_username(username: str) -> Optional[str]:
        """
        Sanitize and validate username
        
        Args:
            username: Raw username input
            
        Returns:
            Sanitized username or None if invalid
        """
        if not username or not isinstance(username, str):
            return None
        
        # Remove leading/trailing whitespace
        username = username.strip()
        
        # Remove HTML entities
        username = html.unescape(username)
        
        # Remove any HTML tags
        username = re.sub(r'<[^>]+>', '', username)
        
        # Check length
        if len(username) > InputSanitizer.MAX_USERNAME_LENGTH:
            logging.warning(f"Username too long: {len(username)} characters")
            return None
        
        # Validate format
        if not InputSanitizer.USERNAME_PATTERN.match(username):
            logging.warning(f"Invalid username format: {username}")
            return None
        
        return username
    
    @staticmethod
    def sanitize_user_id(user_id: Union[str, int]) -> Optional[int]:
        """
        Sanitize and validate user ID
        
        Args:
            user_id: Raw user ID input
            
        Returns:
            Sanitized user ID as int or None if invalid
        """
        if user_id is None:
            return None
        
        # Convert to string for processing
        user_id_str = str(user_id).strip()
        
        # Check length
        if len(user_id_str) > InputSanitizer.MAX_USER_ID_LENGTH:
            logging.warning(f"User ID too long: {len(user_id_str)} characters")
            return None
        
        # Validate format
        if not InputSanitizer.USER_ID_PATTERN.match(user_id_str):
            logging.warning(f"Invalid user ID format: {user_id_str}")
            return None
        
        try:
            return int(user_id_str)
        except (ValueError, TypeError):
            logging.warning(f"Failed to convert user ID to int: {user_id_str}")
            return None
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = None) -> Optional[str]:
        """
        Sanitize and validate text input
        
        Args:
            text: Raw text input
            max_length: Maximum allowed length (default: MAX_TEXT_LENGTH)
            
        Returns:
            Sanitized text or None if invalid
        """
        if not text or not isinstance(text, str):
            return None
        
        # Use default max length if not specified
        if max_length is None:
            max_length = InputSanitizer.MAX_TEXT_LENGTH
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove HTML entities
        text = html.unescape(text)
        
        # Remove any HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Check length
        if len(text) > max_length:
            logging.warning(f"Text too long: {len(text)} characters (max: {max_length})")
            return None
        
        # Basic validation (allow letters, numbers, spaces, and common punctuation)
        if not InputSanitizer.TEXT_PATTERN.match(text):
            logging.warning(f"Text contains invalid characters: {text[:50]}...")
            return None
        
        return text
    
    @staticmethod
    def sanitize_callback_data(callback_data: str) -> Optional[str]:
        """
        Sanitize callback data from Telegram
        
        Args:
            callback_data: Raw callback data
            
        Returns:
            Sanitized callback data or None if invalid
        """
        if not callback_data or not isinstance(callback_data, str):
            return None
        
        # Remove leading/trailing whitespace
        callback_data = callback_data.strip()
        
        # Remove HTML entities
        callback_data = html.unescape(callback_data)
        
        # Remove any HTML tags
        callback_data = re.sub(r'<[^>]+>', '', callback_data)
        
        # Check length (Telegram callback data limit is 64 bytes)
        if len(callback_data.encode('utf-8')) > 64:
            logging.warning(f"Callback data too long: {len(callback_data.encode('utf-8'))} bytes")
            return None
        
        # Allow only alphanumeric characters, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', callback_data):
            logging.warning(f"Callback data contains invalid characters: {callback_data}")
            return None
        
        return callback_data
    
    @staticmethod
    def sanitize_mailbox_id(mailbox_id: Union[str, int]) -> Optional[int]:
        """
        Sanitize and validate mailbox ID
        
        Args:
            mailbox_id: Raw mailbox ID input
            
        Returns:
            Sanitized mailbox ID as int or None if invalid
        """
        if mailbox_id is None:
            return None
        
        # Convert to string for processing
        mailbox_id_str = str(mailbox_id).strip()
        
        # Validate format (positive integer)
        if not re.match(r'^\d+$', mailbox_id_str):
            logging.warning(f"Invalid mailbox ID format: {mailbox_id_str}")
            return None
        
        try:
            mailbox_id_int = int(mailbox_id_str)
            if mailbox_id_int <= 0:
                logging.warning(f"Mailbox ID must be positive: {mailbox_id_int}")
                return None
            return mailbox_id_int
        except (ValueError, TypeError):
            logging.warning(f"Failed to convert mailbox ID to int: {mailbox_id_str}")
            return None
    
    @staticmethod
    def is_safe_input(input_data: str, input_type: str = "text") -> bool:
        """
        Check if input is safe (doesn't contain potentially dangerous content)
        
        Args:
            input_data: Input to check
            input_type: Type of input (text, username, user_id, etc.)
            
        Returns:
            True if input is safe, False otherwise
        """
        if not input_data or not isinstance(input_data, str):
            return False
        
        # Check for potential SQL injection patterns
        sql_patterns = [
            r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
            r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
            r'(\'|\"|;|--|\/\*|\*\/)',
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                logging.warning(f"Potentially unsafe input detected ({input_type}): {input_data[:100]}")
                return False
        
        # Check for potential XSS patterns
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, input_data, re.IGNORECASE):
                logging.warning(f"Potentially unsafe input detected ({input_type}): {input_data[:100]}")
                return False
        
        return True


def sanitize_username(username):
    """Simple username sanitization function"""
    if not username:
        return ""
    return str(username).strip()[:50]

def sanitize_user_id(user_id):
    """Simple user ID sanitization function"""
    if not user_id:
        return 0
    try:
        return int(user_id)
    except (ValueError, TypeError):
        return 0

def sanitize_callback_data(data):
    """Simple callback data sanitization function"""
    if not data:
        return ""
    return str(data).strip()[:64]

def sanitize_user_input(input_data: str, input_type: str = "text") -> Optional[str]:
    """
    Convenience function for sanitizing user input
    
    Args:
        input_data: Raw input data
        input_type: Type of input (text, username, user_id, callback_data, mailbox_id)
        
    Returns:
        Sanitized input or None if invalid
    """
    if not input_data:
        return None
    
    # Check if input is safe first
    if not InputSanitizer.is_safe_input(input_data, input_type):
        return None
    
    # Apply specific sanitization based on type
    if input_type == "username":
        return InputSanitizer.sanitize_username(input_data)
    elif input_type == "user_id":
        result = InputSanitizer.sanitize_user_id(input_data)
        return str(result) if result is not None else None
    elif input_type == "callback_data":
        return InputSanitizer.sanitize_callback_data(input_data)
    elif input_type == "mailbox_id":
        result = InputSanitizer.sanitize_mailbox_id(input_data)
        return str(result) if result is not None else None
    else:  # text
        return InputSanitizer.sanitize_text(input_data)
