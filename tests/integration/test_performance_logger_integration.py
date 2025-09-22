"""
Интеграционные тесты для performance_logger.py
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.performance_logger import PerformanceLogger, performance_logger, get_performance_stats, cleanup_performance_memory, track_performance_object


class TestPerformanceLoggerIntegration:
    """Интеграционные тесты для логгера производительности"""
    
    @pytest.fixture
    def logger_instance(self):
        """Создание экземпляра PerformanceLogger"""
        return PerformanceLogger()
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_slow_operation(self, logger_instance):
        """Тест интеграции логирования медленных операций"""
        # Создаем декоратор для медленной операции
        @logger_instance.log_slow_operation("test_operation", threshold_ms=10.0)
        async def slow_operation():
            await asyncio.sleep(0.1)  # 100ms - медленная операция
            return "result"
        
        # Мокаем логирование
        with patch('app.utils.performance_logger.logger') as mock_logger:
            # Выполняем операцию
            result = await slow_operation()
            
            # Проверяем результат
            assert result == "result"
            
            # Проверяем, что было залогировано предупреждение о медленной операции
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "SLOW OPERATION" in warning_call
            assert "test_operation" in warning_call
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_fast_operation(self, logger_instance):
        """Тест интеграции логирования быстрых операций"""
        # Создаем декоратор для быстрой операции
        @logger_instance.log_slow_operation("test_operation", threshold_ms=100.0)
        async def fast_operation():
            await asyncio.sleep(0.01)  # 10ms - быстрая операция
            return "result"
        
        # Мокаем логирование
        with patch('app.utils.performance_logger.logger') as mock_logger:
            # Выполняем операцию
            result = await fast_operation()
            
            # Проверяем результат
            assert result == "result"
            
            # Проверяем, что не было залогировано предупреждение
            mock_logger.warning.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_memory_management(self, logger_instance):
        """Тест интеграции управления памятью"""
        # Создаем несколько объектов для отслеживания
        test_objects = [{"id": i, "data": f"test_data_{i}"} for i in range(10)]
        
        # Отслеживаем объекты
        refs = []
        for obj in test_objects:
            ref = logger_instance.track_object(obj)
            if ref:
                refs.append(ref)
        
        # Получаем статистику памяти
        memory_stats = logger_instance.get_memory_stats()
        
        # Проверяем статистику
        assert "tracked_objects" in memory_stats
        assert "active_objects" in memory_stats
        assert memory_stats["tracked_objects"] > 0
        assert memory_stats["active_objects"] > 0
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_operation_statistics(self, logger_instance):
        """Тест интеграции статистики операций"""
        # Выполняем несколько операций
        @logger_instance.log_slow_operation("operation_1", threshold_ms=10.0)
        async def operation_1():
            await asyncio.sleep(0.05)
            return "result_1"
        
        @logger_instance.log_slow_operation("operation_2", threshold_ms=10.0)
        async def operation_2():
            await asyncio.sleep(0.02)
            return "result_2"
        
        # Выполняем операции
        await operation_1()
        await operation_2()
        await operation_1()  # Повторная операция
        
        # Получаем статистику памяти (которая включает статистику операций)
        memory_stats = logger_instance.get_memory_stats()
        
        # Проверяем, что статистика операций обновилась
        assert memory_stats["total_operations"] >= 3
        assert memory_stats["total_slow_operations"] >= 0
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_memory_cleanup(self, logger_instance):
        """Тест интеграции очистки памяти"""
        # Создаем много объектов для отслеживания
        test_objects = [{"id": i, "data": f"test_data_{i}"} for i in range(100)]
        
        # Отслеживаем объекты
        for obj in test_objects:
            logger_instance.track_object(obj)
        
        # Получаем статистику до очистки
        stats_before = logger_instance.get_memory_stats()
        
        # Принудительно вызываем очистку памяти
        logger_instance._cleanup_memory_if_needed()
        
        # Получаем статистику после очистки
        stats_after = logger_instance.get_memory_stats()
        
        # Проверяем, что очистка произошла
        assert stats_after["operation_count"] == 0
        assert stats_after["last_cleanup"] > stats_before["last_cleanup"]
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_global_instance(self):
        """Тест интеграции глобального экземпляра"""
        # Создаем декоратор с глобальным экземпляром
        @performance_logger.log_slow_operation("global_operation", threshold_ms=10.0)
        async def global_operation():
            await asyncio.sleep(0.05)
            return "global_result"
        
        # Мокаем логирование
        with patch('app.utils.performance_logger.logger') as mock_logger:
            # Выполняем операцию
            result = await global_operation()
            
            # Проверяем результат
            assert result == "global_result"
            
            # Проверяем, что было залогировано
            mock_logger.warning.assert_called()
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_utility_functions(self):
        """Тест интеграции утилитарных функций"""
        # Тестируем get_performance_stats
        stats = get_performance_stats()
        assert isinstance(stats, dict)
        assert "tracked_objects" in stats
        
        # Тестируем track_performance_object
        test_obj = {"test": "object"}
        ref = track_performance_object(test_obj)
        assert ref is not None
        
        # Тестируем cleanup_performance_memory
        cleanup_performance_memory()
        
        # Проверяем, что функция выполнилась без ошибок
        assert True
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_error_handling(self, logger_instance):
        """Тест обработки ошибок в интеграции"""
        # Создаем декоратор, который генерирует ошибку
        @logger_instance.log_slow_operation("error_operation", threshold_ms=10.0)
        async def error_operation():
            raise ValueError("Test error")
        
        # Мокаем логирование
        with patch('app.utils.performance_logger.logger') as mock_logger:
            # Выполняем операцию и проверяем, что ошибка обработана
            with pytest.raises(ValueError):
                await error_operation()
            
            # Проверяем, что время выполнения все равно было залогировано
            # (декоратор должен работать даже при ошибках)
            mock_logger.warning.assert_called()
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_concurrent_operations(self, logger_instance):
        """Тест конкурентных операций"""
        # Создаем декоратор
        @logger_instance.log_slow_operation("concurrent_operation", threshold_ms=10.0)
        async def concurrent_operation(delay: float):
            await asyncio.sleep(delay)
            return f"result_{delay}"
        
        # Мокаем логирование
        with patch('app.utils.performance_logger.logger') as mock_logger:
            # Создаем несколько конкурентных задач
            tasks = [
                concurrent_operation(0.05),
                concurrent_operation(0.03),
                concurrent_operation(0.07)
            ]
            
            # Выполняем все задачи конкурентно
            results = await asyncio.gather(*tasks)
            
            # Проверяем результаты
            assert len(results) == 3
            assert "result_0.05" in results
            assert "result_0.03" in results
            assert "result_0.07" in results
            
            # Проверяем, что все операции были залогированы
            assert mock_logger.warning.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_performance_logger_integration_memory_tracking_cleanup(self, logger_instance):
        """Тест очистки отслеживаемых объектов"""
        # Создаем объекты
        test_objects = [{"id": i} for i in range(5)]
        
        # Отслеживаем объекты
        refs = []
        for obj in test_objects:
            ref = logger_instance.track_object(obj)
            if ref:
                refs.append(ref)
        
        # Получаем статистику
        stats_before = logger_instance.get_memory_stats()
        assert stats_before["tracked_objects"] > 0
        
        # Удаляем объекты (они должны быть очищены из отслеживания)
        test_objects.clear()
        
        # Принудительно вызываем очистку
        logger_instance._cleanup_memory_if_needed()
        
        # Получаем статистику после очистки
        stats_after = logger_instance.get_memory_stats()
        
        # Проверяем, что отслеживаемые объекты были очищены
        assert stats_after["tracked_objects"] <= stats_before["tracked_objects"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
