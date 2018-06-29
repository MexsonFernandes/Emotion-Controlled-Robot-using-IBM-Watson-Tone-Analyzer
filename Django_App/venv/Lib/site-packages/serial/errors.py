# region Backwards Compatibility
from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals,\
    with_statement

from future import standard_library

standard_library.install_aliases()
from builtins import *
from future.utils import native_str
# endregion

try:
    import typing
except ImportError as e:
    typing = None


class ValidationError(Exception):

    pass


class VersionError(AttributeError):

    pass


class DefinitionExistsError(Exception):

    pass