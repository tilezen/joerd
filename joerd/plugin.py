from importlib import import_module

def plugin(typ, name, func_name):
    """
    Generic pattern for plugins which conform to the same interface. These
    abstract away the details of exactly how something is performed. There are
    several types of these in Joerd:

      * Sources, which know about data sources and how to download them.
      * Outputs, which know about output formats and know how to render
        them.
      * Stores, which know about storing files.
      * Queues, which know about communicating jobs.
    """

    module = import_module('joerd.%s.%s' % (typ, name))
    fn = getattr(module, func_name)
    return fn
