from __future__ import print_function
from collections import deque
import os
import pkgutil
from importlib import import_module
import traceback
import sys

class Condition(object):
    @staticmethod
    def is_module(fullpath):
        """Return whether the full path is a python module."""
        return (
            os.path.isfile(fullpath)
            and (
                fullpath.endswith('.py')
                or (fullpath.endswith('.pyc')
                    and not os.path.isfile(fullpath[:-1]))))

    @staticmethod
    def is_package(fullpath):
        """Return whether the full path is a python package."""
        return (
            os.path.isdir(fullpath)
            and (
                os.path.isfile(os.path.join(fullpath, '__init__.py'))
                or sys.version_info.major > 3.3))

    @classmethod
    def importable(cls, fullpath):
        return cls.is_module(fullpath) or cls.is_package(fullpath)

    @classmethod
    def checkmod(cls, module, fullpath):
        """Return whether the module should be checked.

        module: str
            The name of the package/module to consider.
        fullpath: str
            The full path to the module/package.
        """
        return (
            not module.rsplit('.', 1)[-1].startswith('_')
            and cls.importable(fullpath))

    def __call__(self, package, name, thing):
        """Return whether the item should be returned.

        package: str
            The name of package/module containing the item.
        name: str
            The name of the item.
        thing: object
            The item.
        """
        return not name.startswith('_')

class IsSubclass(Condition):
    def __init__(self, baseclass):
        self.base = baseclass

    def __call__(self, modname, name, thing):
        try:
            return isinstance(thing, type) and issubclass(thing, self.base)
        except Exception:
            return False

def _itermodules(paths, condition=Condition(), prefix=''):
    """Find possible modules on in dirs.

    paths: str or list of strs.
        List of dirs to search.  If a file, use its dirname.
    condition: Condition or callable.
        A function to check whether the module should be searched.
        Search for a 'checkmod' function, otherwise uses condition
        directly as the callable.  It takes 2 arguments: package and
        module.  If package is non-empty, it has a trailing .
    prefix: str
        Prefix for module name (name of parent package if any).
        It will be directly concatenated with name.
    pkgutil docs say iter_modules might not be implemented so have a
        fallback based on os.listdir.
    """
    if isinstance(paths, str):
        paths = [paths]
    try:
        condition = getattr(condition, 'checkmod')
    except AttributeError:
        pass
    try:
        dnames = [os.path.dirname(p) if os.path.isfile(p) else p for p in paths]
        for _, name, ispkg in pkgutil.walk_packages(dnames, prefix):
            yield name
    except Exception:
        traceback.print_exc()
        print('pkgutil failed, falling back to os.listdir', file=sys.stderr)
        # fallback to listdir
        # .py/.pyc files, or packages, non-hidden
        paths = deque([(prefix, path) for path in paths])
        while paths:
            prefix, path = paths.popleft()
            path = os.path.abspath(os.path.normpath(path))
            if os.path.isfile(path):
                path = os.path.dirname(path)
            for fname in os.listdir(path):
                name, ext = os.path.splitext(fname)
                fullpath = os.path.join(path, fname)
                candidate = prefix+name
                if condition(candidate, fullpath):
                    yield candidate
                    if os.path.isdir(fullpath):
                        paths.append((candidate + '.', fullpath))

def find(paths, condition=Condition(), prefix=''):
    """Search for items.

    paths: a str or seq of strs
        Paths to search for items.
    condition: callable(modname, name, obj)
        Return True/False whether the item should be included.
    prefix: str
        The import prefix.  If path points to a path within a package,
        then prefix + name should give the full module/package name.

    If module defines an __all__, only consider those items.  Otherwise,
    use `dir()`
    """
    if prefix and not prefix.endswith('.'):
        prefix += '.'
    for name in _itermodules(paths, condition, prefix):
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
                if condition(name, k, thing):
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
