import importlib

_CONTROLLER_MODULE_NAMES = ['audio', 'code', 'elicast', 'log']

AVAILABLE_CONTROLLERS = []
for module_name in _CONTROLLER_MODULE_NAMES:
    module = importlib.import_module('.' + module_name, __name__)
    AVAILABLE_CONTROLLERS.append(module.controller)
