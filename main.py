import os
import sys
import inspect
import importlib
import json
import dis
import types
from pathlib import Path
import pkgutil

class CompletionGenerator:
    def __init__(self):
        self.completions = {
            "built_ins": self._get_built_ins(),
            "keywords": self._get_keywords(),
            "libraries": {},
            "functions": {},
            "classes": {},
            "vars": {}
        }
        
    def _get_built_ins(self):
        """Python 기본 내장 함수들 수집"""
        built_ins = {}
        for attrname in dir(__builtins__):
            if attrname.startswith('_'):
                continue
            obj = getattr(__builtins__, attrname)
            if callable(obj):
                doc = str(obj.__doc__).split('\n')[0] if obj.__doc__ else ""
                built_ins[attrname] = {
                    "type": "built_in",
                    "doc": doc
                }
        return built_ins
    
    def _get_keywords(self):
        """Python 키워드 수집"""
        import keyword
        return {k: {"type": "keyword"} for k in keyword.kwlist}
    
    def analyze_module(self, module_name, module_obj):
        """모듈 분석해서 함수와 클래스 정보 추출"""
        module_info = {
            "functions": {},
            "classes": {},
            "vars": {}
        }
        
        for name, obj in inspect.getmembers(module_obj):
            # private 멤버는 건너뜀
            if name.startswith('_'):
                continue
                
            elif inspect.isfunction(obj):
                sig = str(inspect.signature(obj))
                doc = str(obj.__doc__).split('\n')[0] if obj.__doc__ else ""
                module_info["functions"][name] = {
                    "signature": sig,
                    "doc": doc,
                    "module": module_name
                }
                
            elif inspect.isclass(obj):
                methods = {}
                for method_name, method_obj in inspect.getmembers(obj, inspect.isfunction):
                    if not method_name.startswith('_'):
                        try:
                            sig = str(inspect.signature(method_obj))
                            doc = str(method_obj.__doc__).split('\n')[0] if method_obj.__doc__ else ""
                            methods[method_name] = {
                                "signature": sig,
                                "doc": doc
                            }
                        except ValueError:
                            continue
                        
                module_info["classes"][name] = {
                    "methods": methods,
                    "doc": str(obj.__doc__).split('\n')[0] if obj.__doc__ else "",
                    "module": module_name
                }

            elif not inspect.isbuiltin(obj):
                doc = str(obj.__doc__).split('\n')[0] if obj.__doc__ else ""
                module_info["vars"][name] = {
                    "doc": doc,
                    "type": type(obj).__name__,
                    "module": module_name
                }
                
        return module_info
    
    def scan_libraries(self):
        for module_name, module in sys.modules.items():
            # private 멤버는 건너뜀
            if module_name.startswith('_'):
                continue
            try:
                # 모듈에 대한 함수 목록을 추출
                if module:
                    module_info = self.analyze_module(module_name, module)
                
                    # 라이브러리 정보 저장
                    self.completions["libraries"][module_name] = {
                        "type": "module",
                        "doc": str(module.__doc__).split('\n')[0] if module.__doc__ else ""
                    }
                    # 함수와 클래스 정보 저장
                    self.completions["functions"].update(module_info["functions"])
                    self.completions["classes"].update(module_info["classes"])
                    self.completions["vars"].update(module_info["vars"])
            except Exception as e:
                # 오류가 발생한 모듈은 건너뜀
                continue
                
    def save_completions(self, output_file):
        """결과를 JSON 파일로 저장"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.completions, f, indent=2, ensure_ascii=False)

def main():
    output_file = sys.argv[2] if len(sys.argv) > 2 else "completions.json"
    
    generator = CompletionGenerator()
    generator.scan_libraries()
    generator.save_completions(output_file)

main()
