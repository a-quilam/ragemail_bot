"""
Resource management utilities for proper cleanup and memory management
"""
import asyncio
import gc
import logging
import weakref
from typing import Any, Dict, List, Optional, Set, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import time


@dataclass
class ResourceInfo:
    """Information about a managed resource"""
    name: str
    resource: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    cleanup_func: Optional[Callable] = None
    is_critical: bool = False


class ResourceManager:
    """Manages resources and ensures proper cleanup"""
    
    def __init__(self, max_resources: int = 1000, cleanup_interval: int = 300):
        self._resources: Dict[str, ResourceInfo] = {}
        self._max_resources = max_resources
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        self._cleanup_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    async def register_resource(
        self, 
        name: str, 
        resource: Any, 
        cleanup_func: Optional[Callable] = None,
        is_critical: bool = False
    ) -> bool:
        """
        Register a resource for management
        
        Args:
            name: Unique name for the resource
            resource: The resource to manage
            cleanup_func: Optional cleanup function
            is_critical: Whether this resource is critical
            
        Returns:
            True if registered successfully, False otherwise
        """
        async with self._cleanup_lock:
            if self._shutdown:
                logging.warning(f"Cannot register resource {name}: manager is shutting down")
                return False
            
            if name in self._resources:
                logging.warning(f"Resource {name} already registered, replacing")
                await self._cleanup_resource(name)
            
            # Check if we need to cleanup old resources
            if len(self._resources) >= self._max_resources:
                await self._cleanup_old_resources()
            
            self._resources[name] = ResourceInfo(
                name=name,
                resource=resource,
                created_at=time.time(),
                last_accessed=time.time(),
                cleanup_func=cleanup_func,
                is_critical=is_critical
            )
            
            logging.debug(f"Registered resource: {name}")
            return True
    
    async def get_resource(self, name: str) -> Optional[Any]:
        """
        Get a managed resource
        
        Args:
            name: Name of the resource
            
        Returns:
            The resource or None if not found
        """
        if name not in self._resources:
            return None
        
        resource_info = self._resources[name]
        resource_info.last_accessed = time.time()
        resource_info.access_count += 1
        
        return resource_info.resource
    
    async def unregister_resource(self, name: str) -> bool:
        """
        Unregister and cleanup a resource
        
        Args:
            name: Name of the resource
            
        Returns:
            True if unregistered successfully, False otherwise
        """
        async with self._cleanup_lock:
            if name not in self._resources:
                return False
            
            await self._cleanup_resource(name)
            del self._resources[name]
            logging.debug(f"Unregistered resource: {name}")
            return True
    
    async def _cleanup_resource(self, name: str):
        """Cleanup a specific resource"""
        if name not in self._resources:
            return
        
        resource_info = self._resources[name]
        
        try:
            if resource_info.cleanup_func:
                if asyncio.iscoroutinefunction(resource_info.cleanup_func):
                    await resource_info.cleanup_func(resource_info.resource)
                else:
                    resource_info.cleanup_func(resource_info.resource)
            
            # Clear the resource reference
            resource_info.resource = None
            
        except Exception as e:
            logging.error(f"Error cleaning up resource {name}: {e}")
    
    async def _cleanup_old_resources(self):
        """Cleanup old, unused resources"""
        current_time = time.time()
        resources_to_remove = []
        
        for name, resource_info in self._resources.items():
            # Don't cleanup critical resources
            if resource_info.is_critical:
                continue
            
            # Cleanup resources that haven't been accessed recently
            if current_time - resource_info.last_accessed > self._cleanup_interval:
                resources_to_remove.append(name)
        
        # Remove up to 20% of resources to make room
        max_remove = max(1, len(self._resources) // 5)
        resources_to_remove = resources_to_remove[:max_remove]
        
        for name in resources_to_remove:
            await self._cleanup_resource(name)
            del self._resources[name]
            logging.debug(f"Cleaned up old resource: {name}")
    
    async def cleanup_all(self):
        """Cleanup all managed resources"""
        async with self._cleanup_lock:
            for name in list(self._resources.keys()):
                await self._cleanup_resource(name)
            
            self._resources.clear()
            logging.info("Cleaned up all resources")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get resource management statistics"""
        current_time = time.time()
        total_resources = len(self._resources)
        critical_resources = sum(1 for r in self._resources.values() if r.is_critical)
        
        return {
            "total_resources": total_resources,
            "critical_resources": critical_resources,
            "max_resources": self._max_resources,
            "cleanup_interval": self._cleanup_interval,
            "last_cleanup": self._last_cleanup,
            "resources": {
                name: {
                    "created_at": info.created_at,
                    "last_accessed": info.last_accessed,
                    "access_count": info.access_count,
                    "is_critical": info.is_critical,
                    "age_seconds": current_time - info.created_at,
                    "idle_seconds": current_time - info.last_accessed
                }
                for name, info in self._resources.items()
            }
        }
    
    async def shutdown(self):
        """Shutdown the resource manager"""
        self._shutdown = True
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        await self.cleanup_all()


# Global resource manager instance
_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance"""
    return _resource_manager


@asynccontextmanager
async def managed_resource(
    name: str, 
    resource: Any, 
    cleanup_func: Optional[Callable] = None,
    is_critical: bool = False
):
    """
    Context manager for automatic resource management
    
    Args:
        name: Unique name for the resource
        resource: The resource to manage
        cleanup_func: Optional cleanup function
        is_critical: Whether this resource is critical
    """
    manager = get_resource_manager()
    
    try:
        await manager.register_resource(name, resource, cleanup_func, is_critical)
        yield resource
    finally:
        await manager.unregister_resource(name)


class MemoryManager:
    """Memory management utilities"""
    
    @staticmethod
    async def cleanup_memory():
        """Force garbage collection and memory cleanup"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Log memory usage
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            logging.info(f"Memory cleanup: collected {collected} objects, "
                        f"RSS: {memory_info.rss / 1024 / 1024:.1f}MB, "
                        f"VMS: {memory_info.vms / 1024 / 1024:.1f}MB")
            
            return {
                "collected_objects": collected,
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024
            }
            
        except ImportError:
            # psutil not available, just do basic cleanup
            collected = gc.collect()
            logging.info(f"Memory cleanup: collected {collected} objects")
            return {"collected_objects": collected}
        except Exception as e:
            logging.error(f"Error during memory cleanup: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_memory_usage() -> Dict[str, float]:
        """Get current memory usage"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}


class ConnectionPool:
    """Simple connection pool for database connections"""
    
    def __init__(self, max_connections: int = 10):
        self._connections: List[Any] = []
        self._max_connections = max_connections
        self._lock = asyncio.Lock()
    
    async def get_connection(self) -> Optional[Any]:
        """Get a connection from the pool"""
        async with self._lock:
            if self._connections:
                return self._connections.pop()
            return None
    
    async def return_connection(self, connection: Any):
        """Return a connection to the pool"""
        async with self._lock:
            if len(self._connections) < self._max_connections:
                self._connections.append(connection)
    
    async def cleanup(self):
        """Cleanup all connections in the pool"""
        async with self._lock:
            for connection in self._connections:
                try:
                    if hasattr(connection, 'close'):
                        if asyncio.iscoroutinefunction(connection.close):
                            await connection.close()
                        else:
                            connection.close()
                except Exception as e:
                    logging.error(f"Error closing connection: {e}")
            
            self._connections.clear()


# Global connection pool
_connection_pool = ConnectionPool()


def get_connection_pool() -> ConnectionPool:
    """Get the global connection pool"""
    return _connection_pool


async def cleanup_all_resources():
    """Cleanup all managed resources"""
    manager = get_resource_manager()
    await manager.cleanup_all()
    
    pool = get_connection_pool()
    await pool.cleanup()
    
    await MemoryManager.cleanup_memory()
    
    logging.info("All resources cleaned up")
