import json
import aiosqlite
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import hashlib

class BackupManager:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def export_data(self) -> Dict[str, Any]:
        """Экспортировать все критически важные данные"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "users": [],
            "mailboxes": [],
            "aliases": [],
            "user_mailbox_bindings": []
        }

        # Экспорт пользователей
        async with self.db.execute("SELECT user_id, role, active_mailbox_id, last_bind_mailbox_id, username FROM users") as cursor:
            async for row in cursor:
                data["users"].append({
                    "user_id": row[0],
                    "role": row[1],
                    "active_mailbox_id": row[2],
                    "last_bind_mailbox_id": row[3],
                    "username": row[4]
                })

        # Экспорт ящиков
        async with self.db.execute("SELECT id, title, channel_id, stat_day, stat_time, creator_id FROM mailboxes") as cursor:
            async for row in cursor:
                data["mailboxes"].append({
                    "id": row[0],
                    "title": row[1],
                    "channel_id": row[2],
                    "stat_day": row[3],
                    "stat_time": row[4],
                    "creator_id": row[5]
                })

        # Экспорт алиасов
        async with self.db.execute("SELECT user_id, alias, valid_day FROM aliases") as cursor:
            async for row in cursor:
                data["aliases"].append({
                    "user_id": row[0],
                    "alias": row[1],
                    "valid_day": row[2]
                })

        # Экспорт привязок пользователей к ящикам (из таблицы users)
        async with self.db.execute("SELECT user_id, active_mailbox_id, last_bind_mailbox_id FROM users WHERE active_mailbox_id IS NOT NULL OR last_bind_mailbox_id IS NOT NULL") as cursor:
            async for row in cursor:
                if row[1] or row[2]:  # Если есть привязки
                    data["user_mailbox_bindings"].append({
                        "user_id": row[0],
                        "active_mailbox_id": row[1],
                        "last_bind_mailbox_id": row[2]
                    })

        # Добавляем контрольную сумму
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        data["checksum"] = hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        
        return data

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Вычислить контрольную сумму данных"""
        # Создаем копию без checksum для вычисления
        data_copy = {k: v for k, v in data.items() if k != "checksum"}
        data_str = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def verify_backup_integrity(self, data: Dict[str, Any]) -> bool:
        """Проверить целостность бэкапа"""
        if "checksum" not in data:
            return False
        
        expected_checksum = data["checksum"]
        actual_checksum = self._calculate_checksum(data)
        
        return expected_checksum == actual_checksum

    def validate_backup_structure(self, data: Dict[str, Any]) -> List[str]:
        """Проверить структуру бэкапа и вернуть список ошибок"""
        errors = []
        
        # Проверяем обязательные поля
        required_fields = ["exported_at", "users", "mailboxes", "aliases", "user_mailbox_bindings"]
        for field in required_fields:
            if field not in data:
                errors.append(f"Отсутствует обязательное поле: {field}")
        
        # Проверяем типы данных
        if "users" in data and not isinstance(data["users"], list):
            errors.append("Поле 'users' должно быть списком")
        
        if "mailboxes" in data and not isinstance(data["mailboxes"], list):
            errors.append("Поле 'mailboxes' должно быть списком")
        
        if "aliases" in data and not isinstance(data["aliases"], list):
            errors.append("Поле 'aliases' должно быть списком")
        
        # Проверяем структуру пользователей
        if "users" in data:
            for i, user in enumerate(data["users"]):
                if not isinstance(user, dict):
                    errors.append(f"Пользователь {i} должен быть объектом")
                    continue
                
                required_user_fields = ["user_id", "role"]
                for field in required_user_fields:
                    if field not in user:
                        errors.append(f"Пользователь {i}: отсутствует поле {field}")
        
        return errors

    async def save_backup(self, backup_dir: str = "backups") -> str:
        """Сохранить бэкап в файл"""
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{backup_dir}/backup_{timestamp}.json"
        
        data = await self.export_data()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filename

    async def import_data(self, data: Dict[str, Any]) -> bool:
        """Импортировать данные в базу"""
        try:
            # Очистка существующих данных (кроме системных)
            await self.db.execute("DELETE FROM users")
            await self.db.execute("DELETE FROM mailboxes")
            await self.db.execute("DELETE FROM aliases")
            await self.db.execute("DELETE FROM mailbox_button_configs")
            
            # Импорт пользователей
            for user in data.get("users", []):
                await self.db.execute(
                    "INSERT INTO users (user_id, role, active_mailbox_id, last_bind_mailbox_id, username) VALUES (?, ?, ?, ?, ?)",
                    (user["user_id"], user["role"], user["active_mailbox_id"], user["last_bind_mailbox_id"], user["username"])
                )

            # Импорт ящиков
            for mailbox in data.get("mailboxes", []):
                await self.db.execute(
                    "INSERT INTO mailboxes (id, title, channel_id, stat_day, stat_time, creator_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (mailbox["id"], mailbox["title"], mailbox["channel_id"], mailbox["stat_day"], mailbox["stat_time"], mailbox["creator_id"])
                )

            # Импорт алиасов
            for alias in data.get("aliases", []):
                await self.db.execute(
                    "INSERT INTO aliases (user_id, alias, valid_day) VALUES (?, ?, ?)",
                    (alias["user_id"], alias["alias"], alias["valid_day"])
                )

            await self.db.commit()
            return True
            
        except Exception as e:
            print(f"Ошибка импорта данных: {e}")
            await self.db.rollback()
            return False

    async def load_backup(self, filename: str) -> bool:
        """Загрузить бэкап из файла с проверкой целостности"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру
            structure_errors = self.validate_backup_structure(data)
            if structure_errors:
                print(f"Ошибки структуры бэкапа: {structure_errors}")
                return False
            
            # Проверяем целостность
            if not self.verify_backup_integrity(data):
                print("Ошибка целостности бэкапа: контрольная сумма не совпадает")
                return False
            
            return await self.import_data(data)
        except Exception as e:
            print(f"Ошибка загрузки бэкапа: {e}")
            return False

    async def verify_backup_file(self, filename: str) -> Dict[str, Any]:
        """Проверить файл бэкапа и вернуть результат проверки"""
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {}
        }
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру
            structure_errors = self.validate_backup_structure(data)
            if structure_errors:
                result["errors"].extend(structure_errors)
                return result
            
            # Проверяем целостность
            if not self.verify_backup_integrity(data):
                result["errors"].append("Контрольная сумма не совпадает")
                return result
            
            # Собираем информацию о бэкапе
            result["info"] = {
                "exported_at": data.get("exported_at"),
                "users_count": len(data.get("users", [])),
                "mailboxes_count": len(data.get("mailboxes", [])),
                "aliases_count": len(data.get("aliases", [])),
                "bindings_count": len(data.get("user_mailbox_bindings", []))
            }
            
            result["valid"] = True
            
        except FileNotFoundError:
            result["errors"].append("Файл бэкапа не найден")
        except json.JSONDecodeError:
            result["errors"].append("Файл не является валидным JSON")
        except Exception as e:
            result["errors"].append(f"Ошибка чтения файла: {e}")
        
        return result
