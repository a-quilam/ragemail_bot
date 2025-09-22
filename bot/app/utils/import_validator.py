"""
Import validation utility to check if all required modules are available
"""
import importlib
import logging
from typing import List, Dict, Any


class ImportValidator:
    """Validates that all required imports are available"""
    
    def __init__(self):
        self.required_modules = [
            'app.utils.circuit_breaker',
            'app.utils.rate_limiter', 
            'app.utils.input_sanitizer',
            'app.utils.output_validator',
            'app.utils.resource_manager',
            'app.utils.rollback_manager',
            'app.utils.concurrency_manager',
            'app.utils.transaction_manager',
            'app.utils.backup_manager',
            'app.utils.health_checks'
        ]
        
        self.required_functions = {
            'app.utils.circuit_breaker': ['get_breaker', 'CircuitBreaker'],
            'app.utils.rate_limiter': ['get_admin_limiter', 'get_stats_limiter', 'check_rate_limit'],
            'app.utils.input_sanitizer': ['InputSanitizer', 'sanitize_user_input'],
            'app.utils.output_validator': ['OutputValidator', 'validate_output'],
            'app.utils.resource_manager': ['get_resource_manager', 'MemoryManager'],
            'app.utils.rollback_manager': ['get_rollback_manager', 'create_admin_removal_rollback'],
            'app.utils.concurrency_manager': ['get_concurrency_manager', 'lock'],
            'app.utils.transaction_manager': ['DatabaseTransaction', 'execute_in_transaction'],
            'app.utils.backup_manager': ['get_backup_manager', 'auto_backup_database'],
            'app.utils.health_checks': ['HealthChecker', 'check_database_health']
        }
    
    def validate_all_imports(self) -> Dict[str, Any]:
        """Validate all required imports and return status"""
        results = {
            'all_valid': True,
            'missing_modules': [],
            'missing_functions': {},
            'available_modules': [],
            'errors': []
        }
        
        for module_name in self.required_modules:
            try:
                module = importlib.import_module(module_name)
                results['available_modules'].append(module_name)
                
                # Check required functions
                missing_functions = []
                if module_name in self.required_functions:
                    for func_name in self.required_functions[module_name]:
                        if not hasattr(module, func_name):
                            missing_functions.append(func_name)
                
                if missing_functions:
                    results['missing_functions'][module_name] = missing_functions
                    results['all_valid'] = False
                
            except ImportError as e:
                results['missing_modules'].append(module_name)
                results['errors'].append(f"Failed to import {module_name}: {e}")
                results['all_valid'] = False
            except Exception as e:
                results['errors'].append(f"Error validating {module_name}: {e}")
                results['all_valid'] = False
        
        return results
    
    def validate_specific_import(self, module_name: str) -> bool:
        """Validate a specific module import"""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
    
    def get_fallback_status(self) -> Dict[str, Any]:
        """Check if fallback implementations are being used"""
        fallback_status = {
            'using_fallbacks': False,
            'fallback_modules': []
        }
        
        # Check if we're using fallback implementations
        try:
            from app.utils import get_breaker
            # If we can import from the main utils module, check if it's a fallback
            if hasattr(get_breaker, '__module__') and 'fallback' in str(get_breaker.__module__):
                fallback_status['using_fallbacks'] = True
                fallback_status['fallback_modules'].append('circuit_breaker')
        except ImportError:
            pass
        
        return fallback_status
    
    def log_validation_results(self, results: Dict[str, Any]):
        """Log validation results"""
        if results['all_valid']:
            logging.info("✅ All required imports are available")
        else:
            logging.warning("⚠️ Some imports are missing or have issues:")
            
            if results['missing_modules']:
                logging.warning(f"Missing modules: {results['missing_modules']}")
            
            if results['missing_functions']:
                for module, functions in results['missing_functions'].items():
                    logging.warning(f"Missing functions in {module}: {functions}")
            
            if results['errors']:
                for error in results['errors']:
                    logging.error(f"Import error: {error}")
    
    def create_import_report(self) -> str:
        """Create a detailed import report"""
        results = self.validate_all_imports()
        fallback_status = self.get_fallback_status()
        
        report = []
        report.append("=" * 50)
        report.append("IMPORT VALIDATION REPORT")
        report.append("=" * 50)
        
        if results['all_valid']:
            report.append("✅ STATUS: All imports are valid")
        else:
            report.append("❌ STATUS: Some imports have issues")
        
        report.append(f"\n📊 SUMMARY:")
        report.append(f"  - Total modules checked: {len(self.required_modules)}")
        report.append(f"  - Available modules: {len(results['available_modules'])}")
        report.append(f"  - Missing modules: {len(results['missing_modules'])}")
        report.append(f"  - Modules with missing functions: {len(results['missing_functions'])}")
        
        if results['available_modules']:
            report.append(f"\n✅ AVAILABLE MODULES:")
            for module in results['available_modules']:
                report.append(f"  - {module}")
        
        if results['missing_modules']:
            report.append(f"\n❌ MISSING MODULES:")
            for module in results['missing_modules']:
                report.append(f"  - {module}")
        
        if results['missing_functions']:
            report.append(f"\n⚠️ MODULES WITH MISSING FUNCTIONS:")
            for module, functions in results['missing_functions'].items():
                report.append(f"  - {module}: {functions}")
        
        if fallback_status['using_fallbacks']:
            report.append(f"\n🔄 FALLBACK STATUS:")
            report.append(f"  - Using fallback implementations: {fallback_status['using_fallbacks']}")
            if fallback_status['fallback_modules']:
                report.append(f"  - Fallback modules: {fallback_status['fallback_modules']}")
        
        if results['errors']:
            report.append(f"\n🚨 ERRORS:")
            for error in results['errors']:
                report.append(f"  - {error}")
        
        report.append("=" * 50)
        
        return "\n".join(report)


# Global validator instance
_import_validator = ImportValidator()


def validate_imports() -> Dict[str, Any]:
    """Validate all imports and return results"""
    return _import_validator.validate_all_imports()


def create_import_report() -> str:
    """Create and return import validation report"""
    return _import_validator.create_import_report()


def log_import_status():
    """Log current import status"""
    results = validate_imports()
    _import_validator.log_validation_results(results)
    
    if not results['all_valid']:
        report = create_import_report()
        logging.warning(f"Import validation report:\n{report}")


# Auto-validate on import
if __name__ != "__main__":
    log_import_status()
