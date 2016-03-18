from importlib import import_module

def plugin(typ, name, func_name):
    module = import_module('joerd.%s.%s' % (typ, name))
    fn = getattr(module, func_name)
    return fn
