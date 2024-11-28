import os
import sys
import inspect
import importlib
import pkgutil
import json
from types import ModuleType, GetSetDescriptorType, MemberDescriptorType
from typing import Any, Dict, Set

class LibraryAnalyzer:
    def __init__(self):
        self.analyzed_modules: Set[str] = set()
        self.result: Dict[str, Dict] = {
            'keywords': self._get_keywords(),
            'modules': {}
        }
        self.original_source: Set[str] = set()
    
    def _get_keywords(self):
        import keyword
        return {k: {"type": "keyword"} for k in keyword.kwlist}
    
    def is_valid_identifier(self, name: str) -> bool:
        """Check if the name is a valid Python identifier and not a private/special name."""
        return (name.isidentifier() and 
                not name.startswith('_') and 
                not name.endswith('_'))
    
    def get_original_module(self, obj: Any) -> str:
        """Get the original module where an object was defined."""
        try:
            if hasattr(obj, '__module__'):
                return obj.__module__
            return None
        except:
            return None
    
    def get_module_items(self, module: ModuleType) -> Dict[str, Dict]:
        """Extract classes, functions, and variables from a module."""
        items = {
            'classes': {},
            'functions': {},
            'variables': {}
        }
        
        for name, obj in inspect.getmembers(module):
            if not self.is_valid_identifier(name):
                continue

            # Get the original module of the object
            original_module = self.get_original_module(obj)
            source_name = f'{original_module}.{name}'
            
            # Skip if this object is imported from another module we're analyzing
            if original_module and original_module != module.__name__ and source_name in self.original_source:
                continue

            self.original_source.add(source_name)


            if inspect.isclass(obj):
                methods = {}
                for method_name, method_obj in inspect.getmembers(obj):
                    if not self.is_valid_identifier(method_name):
                        continue

                    if inspect.isfunction(method_obj):
                        try:
                            signature = str(inspect.signature(method_obj))
                            
                            methods[method_name] = {
                                'doc': inspect.getdoc(method_obj) or '',
                                'signature': signature,
                            }
                        except ValueError:
                            continue
                
                items['classes'][name] = {
                    'doc': inspect.getdoc(obj) or '',
                    'methods': methods,
                    'from': original_module or module.__name__
                }
                
            elif inspect.isfunction(obj):
                try:
                    signature = str(inspect.signature(obj))
                    items['functions'][name] = {
                        'doc': inspect.getdoc(obj) or '',
                        'signature': signature,
                        'from': original_module or module.__name__
                    }
                except ValueError:
                    continue
                    
            elif not inspect.ismodule(obj) and not inspect.isbuiltin(obj):
                try:
                    type_name = type(obj).__name__
                    items['variables'][name] = {
                        'doc': inspect.getdoc(obj) or '',
                        'type': type_name,
                        'from': original_module or module.__name__
                    }
                except:
                    continue

        
        return items
    
    def analyze_module(self, module_name: str) -> None:
        """Analyze a single module and its submodules."""
        if module_name in self.analyzed_modules:
            return
            
        self.analyzed_modules.add(module_name)
        
        try:
            module = importlib.import_module(module_name)
            self.result['modules'][module_name] = self.get_module_items(module)
            
            # Analyze submodules
            if hasattr(module, '__path__'):
                for _, submodule_name, _ in pkgutil.iter_modules(module.__path__):
                    if not self.is_valid_identifier(submodule_name):
                        continue
                    full_submodule_name = f"{module_name}.{submodule_name}"
                    self.analyze_module(full_submodule_name)
                    
        except Exception as e:
            print(f"Error analyzing module {module_name}: {str(e)}")
    
    def analyze_libraries(self, lib_directory: str) -> None:
        """Analyze all libraries in the given directory."""
        # Add lib directory to Python path
        sys.path.insert(0, lib_directory)
        
        # Find all packages in the lib directory
        for item in os.listdir(lib_directory):
            if item.endswith('.zip'):
                sys.path.insert(0, os.path.join(lib_directory, item))
            
        # Get all available modules
        for _, name, _ in pkgutil.iter_modules():
            if not self.is_valid_identifier(name):
                continue
            self.analyze_module(name)
    
    def save_to_json(self) -> None:
        """Save the analysis results to a JSON file."""
        with open('../output.json', 'w', encoding='utf-8') as f:
            json.dump(self.result, f, indent=2, ensure_ascii=False)

def main():
    # Get the directory where A.exe is located
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_dir = os.path.join(exe_dir, 'lib')
    
    analyzer = LibraryAnalyzer()
    analyzer.analyze_libraries(lib_dir)
    
    # Save results to completion.json in the same directory as A.exe
    analyzer.save_to_json()

main()
