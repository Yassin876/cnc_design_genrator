import sys
sys.path.insert(0, './src')

class MockClass:
    def __init__(self, *args, **kwargs):
        pass
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return MockClass()
    def __call__(self, *args, **kwargs):
        return MockClass()

# Mock Triton Modules
from types import ModuleType
import importlib.machinery

class MockLanguage(ModuleType):
    constexpr = object
    dtype = object
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return MockClass()
    def program_id(self, *args, **kwargs): return 0
    def load(self, *args, **kwargs): return 0
    def store(self, *args, **kwargs): pass
    def arange(self, *args, **kwargs): return []
    def where(self, *args, **kwargs): return 0
    def minimum(self, *args, **kwargs): return 0
    def atomic_min(self, *args, **kwargs): return 0
    def atomic_add(self, *args, **kwargs): return 0
    def ravel(self, *args, **kwargs): return []
    def debug_barrier(self, *args, **kwargs): pass
    def reduce(self, *args, **kwargs): return 0

class MockTriton(ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return MockClass()
    def jit(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f
    def autotune(self, *args, **kwargs):
        return lambda f: f
    def Config(self, *args, **kwargs):
        return object()
    def cdiv(self, a, b):
        return (a + b - 1) // b

class TritonMockLoader:
    def create_module(self, spec):
        fullname = spec.name
        if fullname == "triton":
            m = MockTriton(fullname)
        elif fullname == "triton.language":
            m = MockLanguage(fullname)
        else:
            m = ModuleType(fullname)
            # Define module-level __getattr__(name) securely taking only 1 argument
            def safe_getattr(name):
                if name.startswith("__"):
                    raise AttributeError(name)
                return MockClass()
            m.__getattr__ = safe_getattr
        m.__path__ = []
        m.__spec__ = spec
        return m

    def exec_module(self, module):
        if module.__name__ == "triton":
            module.language = sys.modules.get("triton.language")
        elif module.__name__ == "triton.language":
            pass

class TritonMockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == "triton" or fullname.startswith("triton."):
            return importlib.machinery.ModuleSpec(
                name=fullname,
                loader=TritonMockLoader(),
                is_package=True
            )
        return None

sys.meta_path.insert(0, TritonMockFinder())

# Make sure they are initially populated in sys.modules to trigger loader correctly
import importlib
try:
    importlib.import_module("triton")
    importlib.import_module("triton.language")
except Exception as e:
    print("Warning: pre-import failed:", e)

# Patch find_spec for transformers checks
import importlib.util
orig = importlib.util.find_spec
importlib.util.find_spec = lambda name, pkg=None: None if name in (
    'triton', 'triton.language', 'triton.backends', 'triton.backends.compiler', 'triton.compiler'
) else orig(name, pkg)

import traceback

print("Attempting to import transformers.generation.utils directly...")
try:
    import transformers.generation.utils
    print("transformers.generation.utils imported successfully!")
except Exception:
    traceback.print_exc()

print("Attempting to import GenerationMixin...")
try:
    from transformers.generation import GenerationMixin
    print("GenerationMixin imported successfully!", GenerationMixin)
except Exception:
    traceback.print_exc()
