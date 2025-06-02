import importlib.util
import inspect
import os

package_dir = os.path.dirname(__file__)

# Peter 05/08/2024: This is some code I swiped from stackoverflow that iterated through the package directory here looking at .py files
# It reads each file and imports the classes to add them to the "globals" which we can think of as importing into this namespace
# By doing that, everything is exported and ready to be read as members of this `functions` package.
# TLDR: this does what you would think `from . import *` does
# Benefit here is any file with any class is added to the "exports", so nothing needs to be done after dropping a file in here
for filename in os.listdir(package_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = filename[:-3]  # Remove the .py extension to get the module name
        module_path = os.path.join(package_dir, filename)

        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec:
            continue
        module = importlib.util.module_from_spec(spec)
        if spec.loader:
            spec.loader.exec_module(module)
        for name, value in module.__dict__.items():
            if inspect.isclass(value) and not name.startswith("_"):
                globals()[name] = value
