import os
import pkgutil
from importlib import import_module
import traceback
import sys


def _itermodules(paths, prefix=''):
    """Find possible modules on in dirs.

    paths: list of dirs to search.  If a file, use its dirname.
    prefix: prefix for module name (name of parent package if any)
    pkgutil docs say iter_modules might not be implemented.
    """
    if isinstance(paths, str):
        paths = [paths]
    try:
        for path in paths:
            if os.path.isfile(path):
                path = os.path.dirname(path)
            for _, name, ispkg in iter_modules(path, prefix):
                yield name
    except Exception:
        # fallback to listdir
        # .py/.pyc files, or packages, non-hidden
        for path in paths:
            path = os.path.abspath(os.path.normcase(path))
            for fname in os.listdir(path):
                name, ext = os.path.splitext(fname)
                fullpath = os.path.join(path, fname)
                if (
                        fname.startswith('_')
                        or (
                            os.path.isfile(fullpath)
                            and ext not in ('.py', '.pyc'))
                        or (
                            sys.version_info < (3,3)
                            and not os.path.exists(
                                os.path.join(fullpath, '__init__.py')))):
                    continue
                yield prefix+name

class Condition(object):
    def __call__(self, thing):
        """Return True if thing should be returned.

        Default = return all.
        """
        return True

class IsSubclass(Condition):
    def __init__(self, baseclass):
        self.base = baseclass

    def __call__(self, thing):
        try:
            return isinstance(thing, type) and issubclass(thing, baseclass)
        except Exception:
            return False

def find(paths, condition=Condition(), prefix=''):
    """Search for subclasses of base.

    paths: a str or seq of strs
    condition: callable(name, obj)
        Return True/False if 

    If module defines an __all__, only search those items.
    Otherwise, use `dir()`
    """
    if prefix and not prefix.endswith('.'):
        prefix += '.'
    for name in _itermodules(paths, prefix):
        try:
            module = import_module(name)
        except Exception:
            traceback.print_exc()
            continue
        try:
            keys = module.__all__
        except AttributeError:
            keys = dir(module)
        for k in keys:
            try:
                thing = getattr(module, k)
                if condition(thing):
                    yield k, thing
            except Exception:
                traceback.print_exc()

def get(spec, translate={'np': 'numpy'}):
    """Import an item.

    spec: str
        A ':' separated string of module and items.  The module portion
        is a list of module/packages separated by '.'  These will be
        translated using `translate`.  If using the default, then
        'np.random' will be translated to 'numpy.random'.  The items
        portion is also a '.' separated list.  These will be split and
        successively passed to getattr to find the final item.  If ':'
        is omitted, then assume the items portion is empty, resulting
        in just returning the module.
    """
    parts = spec.split(':', 1)
    modname = '.'.join(translate.get(_, _) for _ in parts[0].split('.'))
    item = import_module(modname)
    if len(parts) > 1 and parts[1]:
        for name in parts[1].split('.'):
            item = getattr(item, name)
    return item
