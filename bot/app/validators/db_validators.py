"""
Валидаторы для данных базы данных
"""
import re
from typing import Any, Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

class ValidationError(Exception):
    """Ошибка валидации данных"""
    pass

class ValidationSeverity(Enum):
    """Уровень серьезности ошибки валидации"""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationResult:
    """Результат валидации"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    severity: ValidationSeverity = ValidationSeverity.ERROR

class BaseValidator:
    """Базовый класс для валидаторов"""
    
    def validate(self, value: Any) -> ValidationResult:
        """
        Валидировать значение.
        
        Args:
            value: Значение для валидации
            
        Returns:
            Результат валидации
        """
        raise NotImplementedError

class UserValidator(BaseValidator):
    """Валидатор для данных пользователей"""
    
    VALID_ROLES = {'user', 'admin', 'superadmin'}
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,32}$')
    
    def validate_user_id(self, user_id: Any) -> ValidationResult:
        """Валидировать ID пользователя"""
        errors = []
        warnings = []
        
        if not isinstance(user_id, int):
            errors.append("user_id должен быть целым числом")
        elif user_id <= 0:
            errors.append("user_id должен быть положительным числом")
        elif user_id > 2**63 - 1:  # Максимальное значение для Telegram user_id
            warnings.append("user_id превышает максимальное значение Telegram")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_role(self, role: Any) -> ValidationResult:
        """Валидировать роль пользователя"""
        errors = []
        warnings = []
        
        if not isinstance(role, str):
            errors.append("role должен быть строкой")
        elif role not in self.VALID_ROLES:
            errors.append(f"role должен быть одним из: {', '.join(self.VALID_ROLES)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_username(self, username: Any) -> ValidationResult:
        """Валидировать имя пользователя"""
        errors = []
        warnings = []
        
        if username is None:
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not isinstance(username, str):
            errors.append("username должен быть строкой")
        elif len(username) < 3:
            errors.append("username должен содержать минимум 3 символа")
        elif len(username) > 32:
            errors.append("username должен содержать максимум 32 символа")
        elif not self.USERNAME_PATTERN.match(username):
            errors.append("username может содержать только буквы, цифры и подчеркивания")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class MailboxValidator(BaseValidator):
    """Валидатор для данных почтовых ящиков"""
    
    TITLE_MAX_LENGTH = 100
    TITLE_MIN_LENGTH = 3
    
    def validate_title(self, title: Any) -> ValidationResult:
        """Валидировать название ящика"""
        errors = []
        warnings = []
        
        if not isinstance(title, str):
            errors.append("title должен быть строкой")
        elif len(title) < self.TITLE_MIN_LENGTH:
            errors.append(f"title должен содержать минимум {self.TITLE_MIN_LENGTH} символа")
        elif len(title) > self.TITLE_MAX_LENGTH:
            errors.append(f"title должен содержать максимум {self.TITLE_MAX_LENGTH} символов")
        elif not title.strip():
            errors.append("title не может быть пустым")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_channel_id(self, channel_id: Any) -> ValidationResult:
        """Валидировать ID канала"""
        errors = []
        warnings = []
        
        if not isinstance(channel_id, int):
            errors.append("channel_id должен быть целым числом")
        elif channel_id >= 0:
            errors.append("channel_id должен быть отрицательным числом (каналы имеют отрицательные ID)")
        elif channel_id < -2**63:
            errors.append("channel_id превышает минимальное значение")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class PostValidator(BaseValidator):
    """Валидатор для данных постов"""
    
    TEXT_MAX_LENGTH = 2000
    ALIAS_MAX_LENGTH = 50
    
    def validate_text(self, text: Any) -> ValidationResult:
        """Валидировать текст поста"""
        errors = []
        warnings = []
        
        if not isinstance(text, str):
            errors.append("text должен быть строкой")
        elif len(text) > self.TEXT_MAX_LENGTH:
            errors.append(f"text должен содержать максимум {self.TEXT_MAX_LENGTH} символов")
        elif not text.strip():
            errors.append("text не может быть пустым")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_alias(self, alias: Any) -> ValidationResult:
        """Валидировать псевдоним"""
        errors = []
        warnings = []
        
        if not isinstance(alias, str):
            errors.append("alias должен быть строкой")
        elif len(alias) > self.ALIAS_MAX_LENGTH:
            errors.append(f"alias должен содержать максимум {self.ALIAS_MAX_LENGTH} символов")
        elif not alias.strip():
            errors.append("alias не может быть пустым")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_ttl(self, ttl: Any) -> ValidationResult:
        """Валидировать время жизни поста"""
        errors = []
        warnings = []
        
        if not isinstance(ttl, int):
            errors.append("ttl должен быть целым числом")
        elif ttl < 60:  # Минимум 1 минута
            errors.append("ttl должен быть минимум 60 секунд")
        elif ttl > 7 * 24 * 3600:  # Максимум 7 дней
            warnings.append("ttl превышает 7 дней")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class StatsValidator(BaseValidator):
    """Валидатор для данных статистики"""
    
    def validate_day(self, day: Any) -> ValidationResult:
        """Валидировать дату"""
        errors = []
        warnings = []
        
        if not isinstance(day, str):
            errors.append("day должен быть строкой")
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', day):
            errors.append("day должен быть в формате YYYY-MM-DD")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_key(self, key: Any) -> ValidationResult:
        """Валидировать ключ статистики"""
        errors = []
        warnings = []
        
        if not isinstance(key, str):
            errors.append("key должен быть строкой")
        elif len(key) > 100:
            errors.append("key должен содержать максимум 100 символов")
        elif not key.strip():
            errors.append("key не может быть пустым")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_count(self, count: Any) -> ValidationResult:
        """Валидировать счетчик"""
        errors = []
        warnings = []
        
        if not isinstance(count, int):
            errors.append("count должен быть целым числом")
        elif count < 0:
            errors.append("count не может быть отрицательным")
        elif count > 1000000:
            warnings.append("count превышает 1,000,000")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class DatabaseValidator:
    """Главный валидатор базы данных"""
    
    def __init__(self):
        self.user_validator = UserValidator()
        self.mailbox_validator = MailboxValidator()
        self.post_validator = PostValidator()
        self.stats_validator = StatsValidator()
    
    def validate_user_data(self, user_data: Dict[str, Any]) -> ValidationResult:
        """Валидировать данные пользователя"""
        all_errors = []
        all_warnings = []
        
        # Валидируем user_id
        if 'user_id' in user_data:
            result = self.user_validator.validate_user_id(user_data['user_id'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем role
        if 'role' in user_data:
            result = self.user_validator.validate_role(user_data['role'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем username
        if 'username' in user_data:
            result = self.user_validator.validate_username(user_data['username'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def validate_mailbox_data(self, mailbox_data: Dict[str, Any]) -> ValidationResult:
        """Валидировать данные ящика"""
        all_errors = []
        all_warnings = []
        
        # Валидируем title
        if 'title' in mailbox_data:
            result = self.mailbox_validator.validate_title(mailbox_data['title'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем channel_id
        if 'channel_id' in mailbox_data:
            result = self.mailbox_validator.validate_channel_id(mailbox_data['channel_id'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def validate_post_data(self, post_data: Dict[str, Any]) -> ValidationResult:
        """Валидировать данные поста"""
        all_errors = []
        all_warnings = []
        
        # Валидируем text
        if 'text' in post_data:
            result = self.post_validator.validate_text(post_data['text'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем alias
        if 'alias' in post_data:
            result = self.post_validator.validate_alias(post_data['alias'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем ttl
        if 'ttl' in post_data:
            result = self.post_validator.validate_ttl(post_data['ttl'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def validate_stats_data(self, stats_data: Dict[str, Any]) -> ValidationResult:
        """Валидировать данные статистики"""
        all_errors = []
        all_warnings = []
        
        # Валидируем day
        if 'day' in stats_data:
            result = self.stats_validator.validate_day(stats_data['day'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем key
        if 'key' in stats_data:
            result = self.stats_validator.validate_key(stats_data['key'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        # Валидируем count
        if 'count' in stats_data:
            result = self.stats_validator.validate_count(stats_data['count'])
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )

# Глобальный экземпляр валидатора
db_validator = DatabaseValidator()

def validate_before_insert(table_name: str, data: Dict[str, Any]) -> ValidationResult:
    """
    Валидировать данные перед вставкой в таблицу.
    
    Args:
        table_name: Название таблицы
        data: Данные для вставки
        
    Returns:
        Результат валидации
    """
    if table_name == 'users':
        return db_validator.validate_user_data(data)
    elif table_name == 'mailboxes':
        return db_validator.validate_mailbox_data(data)
    elif table_name == 'posts':
        return db_validator.validate_post_data(data)
    elif table_name == 'stats':
        return db_validator.validate_stats_data(data)
    else:
        # Для неизвестных таблиц возвращаем успешную валидацию
        return ValidationResult(is_valid=True, errors=[], warnings=[])
