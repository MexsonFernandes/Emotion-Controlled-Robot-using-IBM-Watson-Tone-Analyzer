# region Backwards Compatibility
from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, \
    with_statement

import iso8601
from future import standard_library

standard_library.install_aliases()
from builtins import *
from future.utils import native_str
# endregion

from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urljoin
from urllib.response import addbase

import collections
import json
from base64 import b64encode
from collections import OrderedDict, Callable, Set, Sequence
from copy import deepcopy
from io import IOBase
from itertools import chain

import re
import sys

from numbers import Number

import serial
from serial.utilities import qualified_name, properties_values, read

try:
    import typing
    from typing import Union, Dict, Any, AnyStr
except ImportError:
    typing = Union = Any = AnyStr = None

import yaml

if hasattr(collections, 'Generator'):
    Generator = collections.Generator
else:
    Generator = type(n for n in (1, 2, 3))


def marshal(
    data,  # type: Any
    types=None,  # type: Optional[typing.Sequence[Union[type, serial.properties.Property]]]
    value_types=None,  # type: Optional[typing.Sequence[Union[type, serial.properties.Property]]]
    item_types=None,  # type: Optional[typing.Sequence[Union[type, serial.properties.Property]]]
):
    # type: (...) -> Any
    """
    Recursively converts instances of `serial.model.Object` into JSON/YAML serializable objects.
    """
    if hasattr(data, '_marshal'):
        return data._marshal()
    elif data is None:
        return data
    if isinstance(types, Callable):
        types = types(data)
    if (types is not None) or (item_types is not None) or (value_types is not None):
        if types is not None:
            if (str in types) and (native_str is not str) and (native_str not in types):
                types = tuple(chain(*(
                    ((type_, native_str) if (type_ is str) else (type_,))
                    for type_ in types
                )))
            matched = False
            for type_ in types:
                if isinstance(type_, serial.properties.Property):
                    try:
                        data = type_.marshal(data)
                        matched = True
                        break
                    except TypeError:
                        pass
                elif isinstance(type_, type) and isinstance(data, type_):
                    matched = True
                    break
            if not matched:
                raise TypeError(
                    '%s cannot be interpreted as any of the designated types: %s' % (
                        repr(data),
                        repr(types)
                    )
                )
        if value_types is not None:
            for k, v in data.items():
                data[k] = serial.marshal(v, types=value_types)
        if item_types is not None:
            for i in range(len(data)):
                data[i] = serial.marshal(data[i], types=item_types)
    if isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    elif isinstance(data, native_str):
        return data
    elif isinstance(data, (bytes, bytearray)):
        return str(b64encode(data), 'ascii')
    elif hasattr(data, '__bytes__'):
        return str(b64encode(bytes(data)), 'ascii')
    else:
        return data


def unmarshal(
    data,  # type: Any
    types=None,  # type: Optional[typing.Sequence[Union[type, serial.properties.Property]]]
    value_types=None,  # type: Optional[typing.Sequence[Union[type, serial.properties.Property]]]
    item_types=None,  # type: Optional[typing.Sequence[Union[type, serial.properties.Property]]]
):
    # type: (...) -> typing.Any
    """
    Convert `data` into `serial.model` representations of same.
    """
    if (data is None) or (data is serial.properties.NULL):
        return data
    if isinstance(types, Callable):
        types = types(data)
    if isinstance(data, Generator):
        data = tuple(data)
    if types is None:
        if isinstance(data, (dict, OrderedDict)) and not isinstance(data, Dictionary):
            data = Dictionary(data, value_types=value_types)
        elif isinstance(data, (Set, Sequence)) and (not isinstance(data, (str, bytes, native_str, Array))):
            data = Array(data, item_types=item_types)
        return data
    elif (str in types) and (native_str is not str) and (native_str not in types):
        types = tuple(chain(*(
            ((type_, native_str)  if (type_ is str) else (type_,))
            for type_ in types
        )))
    matched = False
    first_error = None
    if isinstance(data, Model):
        metadata = serial.meta.read(data)
    else:
        metadata = None
    for type_ in types:
        if isinstance(
            type_,
            serial.properties.Property
        ):
            try:
                data = type_.unmarshal(data)
                matched = True
                break
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                first_error = error
                continue
        elif isinstance(type_, type):
            if issubclass(type_, Object) and isinstance(data, (dict, OrderedDict)):
                try:
                    data = type_(data)
                    matched = True
                    break
                except (AttributeError, KeyError, TypeError, ValueError) as error:
                    first_error = error
                    pass
            elif isinstance(data, (dict, OrderedDict, Dictionary)) and issubclass(type_, (dict, OrderedDict, Dictionary)):
                if issubclass(type_, Dictionary):
                    data = type_(data, value_types=value_types)
                else:
                    data = Dictionary(data, value_types=value_types)
                matched = True
                break
            elif (
                isinstance(data, (Set, Sequence, Generator)) and
                (not isinstance(data, (str, bytes, native_str))) and
                issubclass(type_, (Set, Sequence)) and
                (not issubclass(type_, (str, bytes, native_str)))
            ):
                if issubclass(type_, Array):
                    data = type_(data, item_types=item_types)
                else:
                    data = Array(data, item_types=item_types)
                matched = True
                break
            elif isinstance(data, type_):
                matched = True
                if isinstance(data, Decimal):
                    data = float(data)
                break
    if not matched:
        if not matched:
            if len(types) == 1 and (first_error is not None):
                raise first_error
            else:
                data_lines = []
                lines = repr(data).split('\n')
                if len(lines) == 1:
                    data_lines.append(lines[0].lstrip())
                else:
                    data_lines.append('')
                    for line in lines:
                        data_lines.append(
                            '       ' + line
                        )
                types_lines = ['(']
                for type_ in types:
                    if isinstance(type_, type):
                        lines = (qualified_name(type_),)
                    else:
                        lines = repr(type_).split('\n')
                    for line in lines:
                        types_lines.append(
                            '           ' + line
                        )
                    types_lines[-1] += ','
                types_lines.append('       )')
                raise TypeError(
                    '\n   The data provided does not match any of the expected types and/or property definitions:\n' +
                    '     - data: %s\n' % '\n'.join(data_lines) +
                    '     - types: %s' % '\n'.join(types_lines)
                )
    if metadata is not None:
        # TODO: Note sure what this does—write tests, test OAPI without it, etc.
        new_metadata = serial.meta.read(data)
        if new_metadata is not None:
            if metadata is not new_metadata:
                writable = False
                if isinstance(metadata, serial.meta.Object):
                    for property_name, value in properties_values(metadata):
                        try:
                            if getattr(new_metadata, property_name) != value:
                                if not writable:
                                    new_metadata = serial.meta.writable(data)
                                setattr(new_metadata, property_name, value)
                        except AttributeError:
                            pass
                elif isinstance(metadata, serial.meta.Array):
                    pass
                elif isinstance(metadata, serial.meta.Dictionary):
                    pass
    return data


def serialize(data, format_='json'):
    # type: (Any, str, Optional[str]) -> str
    """
    Serializes instances of `serial.model.Object` as JSON or YAML.
    """
    hooks = None
    if isinstance(data, (Object, Dictionary, Array)):
        hooks = serial.hooks.read(data)
        if (hooks is not None) and (hooks.before_serialize is not None):
            data = hooks.before_serialize(data)
    if format_ not in ('json', 'yaml'):  # , 'xml'
        format_ = format_.lower()
        if format_ not in ('json', 'yaml'):
            raise ValueError(
                'Supported `serial.model.serialize()` `format_` values include "json" and "yaml" (not "%s").' %
                format_
            )
    if format_ == 'json':
        data = json.dumps(marshal(data))
    elif format_ == 'yaml':
        data = yaml.dump(marshal(data))
    if (hooks is not None) and (hooks.after_serialize is not None):
        data = hooks.after_serialize(data)
    return data


def deserialize(data, format_):
    # type: (Optional[Union[str, IOBase, addbase]], str) -> Any
    if format_ not in ('json', 'yaml'):  # , 'xml'
        raise NotImplementedError(
            'Deserialization of data in the format %s is not currently supported.' % repr(format_)
        )
    if not isinstance(data, (str, bytes)):
        data = read(data)
    if isinstance(data, bytes):
        data = str(data, encoding='utf-8')
    if isinstance(data, str):
        if format_ == 'json':
            data = json.loads(
                data,
                object_hook=OrderedDict,
                object_pairs_hook=OrderedDict
            )
        elif format_ == 'yaml':
            data = yaml.load(data)
    return data


def detect_format(data):
    # type: (Optional[Union[str, IOBase, addbase]]) -> Tuple[Any, str]
    if not isinstance(data, str):
        try:
            data = serial.utilities.read(data)
        except TypeError:
            return data, None
    formats = ('json', 'yaml')  # , 'xml'
    format_ = None
    for potential_format in formats:
        try:
            data = deserialize(data, potential_format)
            format_ = potential_format
            break
        except ValueError:
            pass
    if format is None:
        raise ValueError(
            'The data provided could not be parsed:\n' + repr(data)
        )
    return data, format_


def validate(
    data,  # type: Union[Object, Array, Dictionary]
    types=None,  # type: Optional[Union[type, serial.properties.Property, Object]]
    raise_errors=True  # type: bool
):
    # type: (...) -> typing.Sequence[str]
    error_messages = []
    error_message = None
    if types is not None:
        if isinstance(types, collections.Callable):
            types = types(data)
        if (str in types) and (native_str is not str) and (native_str not in types):
            types = tuple(chain(*(
                ((type_, native_str)  if (type_ is str) else (type_,))
                for type_ in types
            )))
        valid = False
        for type_ in types:
            if isinstance(type_, type) and isinstance(data, type_):
                valid = True
                break
            elif isinstance(type_, serial.properties.Property):
                if type_.types is None:
                    valid = True
                    break
                try:
                    validate(data, type_.types, raise_errors=True)
                    valid = True
                    break
                except serial.errors.ValidationError:
                    pass
        if not valid:
            error_message = (
                '\n`data` is invalid:\n%s\n`data` must be one of the following types:\n%s.' % (
                    '\n'.join('   ' + line for line in repr(data).split('\n')),
                    '\n'.join(
                        repr(Array(types)).split('\n')[1:-1]
                    )
                )
            )
    if error_message is not None:
        if (not error_messages) or (error_message not in error_messages):
            error_messages.append(error_message)
    if ('_validate' in dir(data)) and callable(data._validate):
        error_messages.extend(
            error_message for error_message in
            data._validate(raise_errors=False)
            if error_message not in error_messages
        )
    if raise_errors and error_messages:
        raise serial.errors.ValidationError('\n' + '\n\n'.join(error_messages))
    return error_messages


def version(data, specification, version_number):
    # type: (Any, str, Union[str, int, typing.Sequence[int]]) -> Any
    """
    Recursively alters instances of `serial.model.Object` according to version_number metadata associated with that
    object's serial.properties.

    Arguments:

        - data

        - specification (str): The specification to which the `version_number` argument applies.

        - version_number (str|int|[int]): A version number represented as text (in the form of integers separated by
          periods), an integer, or a sequence of integers.
    """
    def version_match(property):
        if property.versions is not None:
            version_matched = False
            specification_matched = False
            for version_ in property.versions:
                if version_.specification == specification:
                    specification_matched = True
                    if version_ == version_number:
                        version_matched = True
                        break
            if specification_matched and (not version_matched):
                return False
        return True

    def version_properties(properties):
        # type: (typing.Sequence[serial.properties.Property]) -> Optional[typing.Sequence[serial.meta.Meta]]
        changed = False
        nps = []
        for property in properties:
            if isinstance(property, serial.properties.Property):
                if version_match(property):
                    np = version_property(property)
                    if np is not property:
                        changed = True
                    nps.append(np)
                else:
                    changed = True
            else:
                nps.append(property)
        if changed:
            return tuple(nps)
        else:
            return None

    def version_property(property):
        # type: (serial.properties.Property) -> serial.meta.Meta
        changed = False
        if isinstance(property, serial.properties.Array) and (property.item_types is not None):
            item_types = version_properties(property.item_types)
            if item_types is not None:
                if not changed:
                    property = deepcopy(property)
                property.item_types = item_types
                changed = True
        elif isinstance(property, serial.properties.Dictionary) and (property.value_types is not None):
            value_types = version_properties(property.value_types)
            if value_types is not None:
                if not changed:
                    property = deepcopy(property)
                property.value_types = value_types
                changed = True
        if property.types is not None:
            types = version_properties(property.types)
            if types is not None:
                if not changed:
                    property = deepcopy(property)
                property.types = types
        return property

    if isinstance(data, Model):
        instance_meta = serial.meta.read(data)
        class_meta = serial.meta.read(type(data))
        if isinstance(data, Object):
            for property_name in tuple(instance_meta.properties.keys()):
                property = instance_meta.properties[property_name]
                if version_match(property):
                    np = version_property(property)
                    if np is not property:
                        if instance_meta is class_meta:
                            instance_meta = serial.meta.writable(data)
                        instance_meta.properties[property_name] = np
                else:
                    if instance_meta is class_meta:
                        instance_meta = serial.meta.writable(data)
                    del instance_meta.properties[property_name]
                    version_ = getattr(data, property_name)
                    if version_ is not None:
                        raise serial.errors.VersionError(
                            '%s - the property `%s` is not applicable in %s version %s:\n%s' % (
                                qualified_name(type(data)),
                                property_name,
                                specification,
                                version_number,
                                str(data)
                            )
                        )
                version(getattr(data, property_name), specification, version_number)
        elif isinstance(data, Dictionary):
            if instance_meta.value_types:
                new_value_types = version_properties(instance_meta.value_types)
                if new_value_types:
                    if instance_meta is class_meta:
                        instance_meta = serial.meta.writable(data)
                    instance_meta.value_types = new_value_types
            for version_ in data.values():
                version(version_, specification, version_number)
        elif isinstance(data, Array):
            if instance_meta.item_types:
                new_item_types = version_properties(instance_meta.item_types)
                if new_item_types:
                    if instance_meta is class_meta:
                        instance_meta = serial.meta.writable(data)
                    instance_meta.item_types = new_item_types
            for version_ in data:
                version(version_, specification, version_number)
    elif isinstance(data, (collections.Set, collections.Sequence)) and not isinstance(data, (str, bytes)):
        # for d in data:
        #     version(d, specification, version_number)
        raise ValueError()
    elif isinstance(data, (dict, OrderedDict)):
        # for k, v in data.items():
        #     version(v, specification, version_number)
        raise ValueError()


class Model(object):

    _format = None  # type: Optional[str]
    _meta = None  # type: Optional[serial.meta.Object]
    _hooks = None  # type: Optional[serial.hooks.Object]
    _url = None  # type: Optional[str]
    _xpath = None  # type: Optional[str]
    _pointer = None  # type: Optional[str]

    def __init__(self):
        self._format = None  # type: Optional[str]
        self._meta = None  # type: Optional[serial.meta.Meta]
        self._hooks = None  # type: Optional[serial.hooks.Hooks]
        self._url = None  # type: Optional[str]
        self._xpath = None  # type: Optional[str]
        self._pointer = None  # type: Optional[str]

    def __hash__(self):
        return id(self)


class Object(Model):

    _format = None  # type: Optional[str]
    _meta = None  # type: Optional[serial.meta.Object]
    _hooks = None  # type: Optional[serial.hooks.Object]

    def __init__(
        self,
        _=None,  # type: Optional[Union[str, bytes, dict, typing.Sequence, IO]]
    ):
        self._meta = None  # type: Optional[serial.meta.Object]
        self._hooks = None  # type: Optional[serial.hooks.Object]
        self._url = None  # type: Optional[str]
        self._xpath = None  # type: Optional[str]
        self._pointer = None  # type: Optional[str]
        url = None
        if _ is not None:
            if isinstance(_, Object):
                meta = serial.meta.read(_)
                if serial.meta.read(self) is not meta:
                    serial.meta.write(self, deepcopy(meta))
                hooks = serial.hooks.read(_)
                if serial.hooks.read(self) is not hooks:
                    serial.hooks.write(self, deepcopy(hooks))
                for property_name in meta.properties.keys():
                    try:
                        setattr(self, property_name, getattr(_, property_name))
                    except TypeError as error:
                        label = '\n - %s.%s: ' % (qualified_name(type(self)), property_name)
                        if error.args:
                            error.args = tuple(
                                chain(
                                    (label + error.args[0],),
                                    error.args[1:]
                                )
                            )
                        else:
                            error.args = (label + serialize(_),)
                        raise error
            else:
                if isinstance(_, IOBase):
                    if hasattr(_, 'url'):
                        url = _.url
                    elif hasattr(_, 'name'):
                        url = urljoin('file:', _.name)
                _, format_ = detect_format(_)
                if isinstance(_, dict):
                    for property_name, value in _.items():
                        if value is None:
                            value = serial.properties.NULL
                        try:
                            self[property_name] = value
                        except KeyError as error:
                            if error.args and len(error.args) == 1:
                                error.args = (
                                    r'%s.%s: %s' % (qualified_name(type(self)), error.args[0], repr(_)),
                                )
                            raise error
                else:
                    _dir = tuple(property_name for property_name in dir(_) if property_name[0] != '_')
                    for property_name in serial.meta.writable(self.__class__).properties.keys():
                        if property_name in _dir:
                            setattr(self, getattr(_, property_name))
                if format_ is not None:
                    serial.meta.format_(self, format_)
            if url is not None:
                serial.meta.url(self, url)
            if serial.meta.pointer(self) is None:
                serial.meta.pointer(self, '#')
            if serial.meta.xpath(self) is None:
                serial.meta.xpath(self, '')

    def __setattr__(self, property_name, value):
        # type: (Object, str, Any) -> None
        hooks = serial.hooks.read(self)  # type: serial.hooks.Object
        if hooks and hooks.before_setattr:
            property_name, value = hooks.before_setattr(self, property_name, value)
        if property_name[0] != '_':
            try:
                property_definition = serial.meta.read(self).properties[property_name]
            except KeyError:
                # if value is not None:
                raise KeyError(
                    '`%s` has no attribute "%s".' % (
                        qualified_name(type(self)),
                        property_name
                    )
                )
            if value is not None:
                try:
                    value = property_definition.unmarshal(value)
                    if isinstance(value, Generator):
                        value = tuple(value)
                except (TypeError, ValueError) as error:
                    message = '\n - %s.%s: ' % (
                        qualified_name(type(self)),
                        property_name
                    )
                    if error.args and isinstance(error.args[0], str):
                        error.args = tuple(
                            chain(
                                (message + error.args[0],),
                                error.args[1:]
                            )
                        )
                    else:
                        error.args = (message + repr(value),)
                    raise error
        super().__setattr__(property_name, value)
        if hooks and hooks.after_setattr:
            hooks.after_setattr(self, property_name, value)

    def __setitem__(self, key, value):
        # type: (str, str) -> None
        hooks = serial.hooks.read(self)  # type: serial.hooks.Object
        if hooks and hooks.before_setitem:
            key, value = hooks.before_setitem(self, key, value)
        meta = serial.meta.read(self)
        if key in meta.properties:
            property_name = key
        else:
            property_name = None
            for potential_property_name, property in meta.properties.items():
                if key == property.name:
                    property_name = potential_property_name
                    break
            if property_name is None:
                raise KeyError(
                    '`%s` has no property mapped to the name "%s"' % (
                        qualified_name(type(self)),
                        key
                    )
                )
        setattr(self, property_name, value)
        if hooks and hooks.after_setitem:
            hooks.after_setitem(self, key, value)

    def __delattr__(self, key):
        # type: (str) -> None
        # type: (str, str) -> None
        meta = serial.meta.read(self)
        if key in meta.properties:
            setattr(self, key, None)
        else:
            super().__delattr__(key)


    def __getitem__(self, key):
        # type: (str, str) -> None
        meta = serial.meta.read(self)
        if key in meta.properties:
            property_name = key
        else:
            property_definition = None
            property_name = None
            for pn, pd in meta.properties.items():
                if key == pd.name:
                    property_name = pn
                    property_definition = pd
                    break
            if property_definition is None:
                raise KeyError(
                    '`%s` has no property mapped to the name "%s"' % (
                        qualified_name(type(self)),
                        key
                    )
                )
        return getattr(self, property_name)

    def __copy__(self):
        # type: () -> Object
        return self.__class__(self)

    def __deepcopy__(self, memo=None):
        # type: (Optional[dict]) -> Object
        new_instance = self.__class__()
        instance_meta = serial.meta.read(self)
        class_meta = serial.meta.read(type(self))
        if instance_meta is class_meta:
            meta = class_meta  # type: serial.meta.Object
        else:
            serial.meta.write(new_instance, deepcopy(instance_meta, memo=memo))
            meta = instance_meta  # type: serial.meta.Object
        instance_hooks = serial.hooks.read(self)
        class_hooks = serial.hooks.read(type(self))
        if instance_hooks is not class_hooks:
            serial.hooks.write(new_instance, deepcopy(instance_hooks, memo=memo))
        if meta is not None:
            for property_name in meta.properties.keys():
                try:
                    value = getattr(self, property_name)
                    if value is not None:
                        if not isinstance(value, Callable):
                            value = deepcopy(value, memo=memo)
                            setattr(new_instance, property_name, value)
                except TypeError as error:
                    label = '%s.%s: ' % (qualified_name(type(self)), property_name)
                    if error.args:
                        error.args = tuple(
                            chain(
                                (label + error.args[0],),
                                error.args[1:]
                            )
                        )
                    else:
                        error.args = (label + serialize(self),)
                    raise error
        return new_instance

    def _marshal(self):
        object_ = self
        hooks = serial.hooks.read(object_)
        if (hooks is not None) and (hooks.before_marshal is not None):
            object_ = hooks.before_marshal(object_)
        data = OrderedDict()
        meta = serial.meta.read(object_)
        for property_name, property in meta.properties.items():
            value = getattr(object_, property_name)
            if value is not None:
                key = property.name or property_name
                data[key] = property.marshal(value)
        if (hooks is not None) and (hooks.after_marshal is not None):
            data = hooks.after_marshal(data)
        return data

    def __str__(self):
        return serialize(self)

    def __repr__(self):
        representation = [
            '%s(' % qualified_name(type(self))
        ]
        meta = serial.meta.read(self)
        for property_name in meta.properties.keys():
            value = getattr(self, property_name)
            if value is not None:
                repr_value = (
                    qualified_name(value)
                    if isinstance(value, type) else
                    repr(value)
                )
                repr_value_lines = repr_value.split('\n')
                if len(repr_value_lines) > 2:
                    rvs = [repr_value_lines[0]]
                    for rvl in repr_value_lines[1:]:
                        rvs.append('    ' + rvl)
                    repr_value = '\n'.join(rvs)
                representation.append(
                    '    %s=%s,' % (property_name, repr_value)
                )
        representation.append(')')
        if len(representation) > 2:
            return '\n'.join(representation)
        else:
            return ''.join(representation)

    def __eq__(self, other):
        # type: (Any) -> bool
        if type(self) is not type(other):
            return False
        meta = serial.meta.read(self)
        om = serial.meta.read(other)
        self_properties = set(meta.properties.keys())
        other_properties = set(om.properties.keys())
        for property_name in (self_properties | other_properties):
            value = getattr(self, property_name)
            ov = getattr(other, property_name)
            if value != ov:
                return False
        return True

    def __ne__(self, other):
        # type: (Any) -> bool
        return False if self == other else True

    def __iter__(self):
        meta = serial.meta.read(self)
        for property_name, property in meta.properties.items():
            yield property.name or property_name

    def _validate(self, raise_errors=True):
        # type: (Callable, bool, Optional[list]) -> None
        errors = []
        object_ = self
        hooks = serial.hooks.read(self)
        if (hooks is not None) and (hooks.before_validate is not None):
            object_ = hooks.before_validate(object_)
        meta = serial.meta.read(object_)
        for property_name, property in meta.properties.items():
            value = getattr(object_, property_name)
            if value is None:
                if isinstance(property.required, Callable):
                    required = property.required(object_)
                else:
                    required = property.required
                if required:
                    errors.append(
                        'The property `%s` is required for `%s`:\n%s' % (
                            property_name,
                            qualified_name(type(object_)),
                            str(object_)
                        )
                    )
            else:
                if value is serial.properties.NULL:
                    types = property.types
                    if isinstance(types, collections.Callable):
                        types = types(value)
                    if types is not None:
                        if (str in types) and (native_str is not str) and (native_str not in types):
                            types = tuple(chain(*(
                                ((type_, native_str) if (type_ is str) else (type_,))
                                for type_ in types
                            )))
                        if serial.properties.Null not in types:
                            errors.append(
                                'Null values are not allowed in `%s.%s`, ' % (qualified_name(type(object_)), property_name) +
                                'permitted types include: %s.' % ', '.join(
                                    '`%s`' % qualified_name(type_) for type_ in types
                                )
                            )
                else:
                    try:
                        errors.extend(validate(value, property.types, raise_errors=False))
                    except serial.errors.ValidationError as error:
                        message = '%s.%s:\n' % (qualified_name(type(object_)), property_name)
                        if error.args:
                            error.args = tuple(chain(
                                (error.args[0] + message,),
                                error.args[1:]
                            ))
                        else:
                            error.args = (
                                message,
                            )
        if (hooks is not None) and (hooks.after_validate is not None):
            hooks.after_validate(object_)
        if raise_errors and errors:
            raise serial.errors.ValidationError('\n'.join(errors))
        return errors


class Array(list, Model):

    _format = None  # type: Optional[str]
    _hooks = None  # type: Optional[serial.hooks.Array]
    _meta = None  # type: Optional[serial.meta.Array]

    def __init__(
        self,
        items=None,  # type: Optional[Union[Sequence, Set]]
        item_types=(
            None
        ),  # type: Optional[Union[Sequence[Union[type, serial.properties.Property]], type, serial.properties.Property]]
    ):
        self._meta = None  # type: Optional[serial.meta.Array]
        self._hooks = None  # type: Optional[serial.hooks.Array]
        self._url = None  # type: Optional[str]
        self._xpath = None  # type: Optional[str]
        self._pointer = None  # type: Optional[str]
        url = None
        if isinstance(items, IOBase):
            if hasattr(items, 'url'):
                url = items.url
            elif hasattr(items, 'name'):
                url = urljoin('file:', items.name)
        items, format_ = detect_format(items)
        if item_types is None:
            if isinstance(items, Array):
                m = serial.meta.read(items)
                if serial.meta.read(self) is not m:
                    serial.meta.write(self, deepcopy(m))
        else:
            serial.meta.writable(self).item_types = item_types
        if items is not None:
            for item in items:
                self.append(item)
            if serial.meta.pointer(self) is None:
                serial.meta.pointer(self, '#')
            if serial.meta.xpath(self) is None:
                serial.meta.xpath(self, '')
        if url is not None:
            serial.meta.url(self, url)
        if format_ is not None:
            serial.meta.format_(self, format_)

    def __setitem__(
        self,
        index,  # type: int
        value,  # type: Any
    ):
        hooks = serial.hooks.read(self)  # type: serial.hooks.Object
        if hooks and hooks.before_setitem:
            index, value = hooks.before_setitem(self, index, value)
        m = serial.meta.read(self)
        if m is None:
            item_types = None
        else:
            item_types = m.item_types
        value = unmarshal(value, types=item_types)
        super().__setitem__(index, value)
        if hooks and hooks.after_setitem:
            hooks.after_setitem(self, index, value)

    def append(self, value):
        # type: (Any) -> None
        hooks = serial.hooks.read(self)  # type: serial.hooks.Object
        if hooks and hooks.before_append:
            value = hooks.before_append(self, value)
        m = serial.meta.read(self)
        if m is None:
            item_types = None
        else:
            item_types = m.item_types
        value = unmarshal(value, types=item_types)
        super().append(value)
        if hooks and hooks.after_append:
            hooks.after_append(self, value)

    def __copy__(self):
        # type: () -> Array
        return self.__class__(self)

    def __deepcopy__(self, memo=None):
        # type: (Optional[dict]) -> Array
        new_instance = self.__class__()
        im = serial.meta.read(self)
        cm = serial.meta.read(type(self))
        if im is not cm:
            serial.meta.write(new_instance, deepcopy(im, memo=memo))
        ih = serial.hooks.read(self)
        ch = serial.hooks.read(type(self))
        if ih is not ch:
            serial.hooks.write(new_instance, deepcopy(ih, memo=memo))
        for i in self:
            new_instance.append(deepcopy(i, memo=memo))
        return new_instance

    def _marshal(self):
        a = self
        h = serial.hooks.read(a)
        if (h is not None) and (h.before_marshal is not None):
            a = h.before_marshal(a)
        m = serial.meta.read(a)
        a = tuple(
            marshal(
                i,
                types=None if m is None else m.item_types
            ) for i in a
        )
        if (h is not None) and (h.after_marshal is not None):
            a = h.after_marshal(a)
        return a

    def _validate(
        self,
        raise_errors=True
    ):
        # type: (bool) -> None
        errors = []
        a = self
        h = serial.hooks.read(a)
        if (h is not None) and (h.before_validate is not None):
            a = h.before_validate(a)
        m = serial.meta.read(a)
        if m.item_types is not None:
            for i in a:
                errors.extend(validate(i, m.item_types, raise_errors=False))
        if (h is not None) and (h.after_validate is not None):
            h.after_validate(a)
        if raise_errors and errors:
            raise serial.errors.ValidationError('\n'.join(errors))
        return errors

    def __repr__(self):
        representation = [
            qualified_name(type(self)) + '('
        ]
        if len(self) > 0:
            representation.append('    [')
            for i in self:
                ri = (
                    qualified_name(i) if isinstance(i, type) else
                    repr(i)
                )
                rils = ri.split('\n')
                if len(rils) > 1:
                    ris = [rils[0]]
                    ris += [
                        '        ' + rvl
                        for rvl in rils[1:]
                    ]
                    ri = '\n'.join(ris)
                representation.append(
                    '        %s,' % ri
                )
            im = serial.meta.read(self)
            cm = serial.meta.read(type(self))
            m = None if (im is cm) else im
            representation.append(
                '    ]' + (''
                if m is None or m.item_types is None
                else ',')
            )
        im = serial.meta.read(self)
        cm = serial.meta.read(type(self))
        if im is not cm:
            if im.item_types:
                representation.append(
                    '    item_types=(',
                )
                for it in im.item_types:
                    ri = (
                        qualified_name(it) if isinstance(it, type) else
                        repr(it)
                    )
                    rils = ri.split('\n')
                    if len(rils) > 2:
                        ris = [rils[0]]
                        ris += [
                            '        ' + rvl
                            for rvl in rils[1:-1]
                        ]
                        ris.append('        ' + rils[-1])
                        ri = '\n'.join(ris)
                    representation.append('        %s,' % ri)
                m = serial.meta.read(self)
                if len(m.item_types) > 1:
                    representation[-1] = representation[-1][:-1]
                representation.append('    )')
        representation.append(')')
        if len(representation) > 2:
            return '\n'.join(representation)
        else:
            return ''.join(representation)

    def __eq__(self, other):
        # type: (Any) -> bool
        if type(self) is not type(other):
            return False
        length = len(self)
        if length != len(other):
            return False
        for i in range(length):
            if self[i] != other[i]:
                return False
        return True

    def __ne__(self, other):
        # type: (Any) -> bool
        if self == other:
            return False
        else:
            return True

    def __str__(self):
        return serialize(self)


class Dictionary(OrderedDict, Model):

    _format = None  # type: Optional[str]
    _hooks = None  # type: Optional[serial.hooks.Dictionary]
    _meta = None  # type: Optional[serial.meta.Dictionary]

    def __init__(
        self,
        items=None,  # type: Optional[typing.Mapping]
        value_types=(
            None
        ),  # type: Optional[Union[Sequence[Union[type, serial.properties.Property]], type, serial.properties.Property]]
    ):
        self._meta = None  # type: Optional[serial.meta.Dictionary]
        self._hooks = None  # type: Optional[serial.hooks.Dictionary]
        self._url = None  # type: Optional[str]
        self._xpath = None  # type: Optional[str]
        self._pointer = None  # type: Optional[str]
        url = None
        if isinstance(items, IOBase):
            if hasattr(items, 'url'):
                url = items.url
            elif hasattr(items, 'name'):
                url = urljoin('file:', items.name)
        items, f = detect_format(items)
        if value_types is None:
            if isinstance(items, Dictionary):
                m = serial.meta.read(items)
                if serial.meta.read(self) is not m:
                    serial.meta.write(self, deepcopy(m))
        else:
            serial.meta.writable(self).value_types = value_types
        super().__init__()
        if items is None:
            super().__init__()
        else:
            if isinstance(items, (OrderedDict, Dictionary)):
                items = items.items()
            elif isinstance(items, dict):
                items = sorted(items.items(), key=lambda kv: kv)
            super().__init__(items)
            if serial.meta.pointer(self) is None:
                serial.meta.pointer(self, '#')
            if serial.meta.xpath(self) is None:
                serial.meta.xpath(self, '')
        if url is not None:
            serial.meta.url(self, url)
        if f is not None:
            serial.meta.format_(self, f)

    def __setitem__(
        self,
        key,  # type: int
        value,  # type: Any
    ):
        hooks = serial.hooks.read(self)  # type: serial.hooks.Dictionary
        if hooks and hooks.before_setitem:
            key, value = hooks.before_setitem(self, key, value)
        m = serial.meta.read(self)
        if m is None:
            value_types = None
        else:
            value_types = m.value_types
        try:
            value = unmarshal(
                value,
                types=value_types
            )
        except TypeError as error:
            message = "\n - %s['%s']: " % (
                qualified_name(type(self)),
                key
            )
            if error.args and isinstance(error.args[0], str):
                error.args = tuple(
                    chain(
                        (message + error.args[0],),
                        error.args[1:]
                    )
                )
            else:
                error.args = (message + repr(value),)
            raise error
        super().__setitem__(
            key,
            value
        )
        if hooks and hooks.after_setitem:
            hooks.after_setitem(self, key, value)

    def __copy__(self):
        # type: (Dictionary) -> Dictionary
        new_instance = self.__class__()
        im = serial.meta.read(self)
        cm = serial.meta.read(type(self))
        if im is not cm:
            serial.meta.write(new_instance, im)
        ih = serial.hooks.read(self)
        ch = serial.hooks.read(type(self))
        if ih is not ch:
            serial.hooks.write(new_instance, ih)
        for k, v in self.items():
            new_instance[k] = v
        return new_instance

    def __deepcopy__(self, memo=None):
        # type: (dict) -> Dictionary
        new_instance = self.__class__()
        im = serial.meta.read(self)
        cm = serial.meta.read(type(self))
        if im is not cm:
            serial.meta.write(new_instance, deepcopy(im, memo=memo))
        ih = serial.hooks.read(self)
        ch = serial.hooks.read(type(self))
        if ih is not ch:
            serial.hooks.write(new_instance, deepcopy(ih, memo=memo))
        for k, v in self.items():
            new_instance[k] = deepcopy(v, memo=memo)
        return new_instance

    def _marshal(self):
        d = self
        h = serial.hooks.read(d)
        if (h is not None) and (h.before_marshal is not None):
            d = h.before_marshal(d)
        m = serial.meta.read(d)
        if m is None:
            value_types = None
        else:
            value_types = m.value_types
        d = OrderedDict(
            [
                (
                    k,
                    marshal(v, types=value_types)
                ) for k, v in d.items()
            ]
        )
        if (h is not None) and (h.after_marshal is not None):
            d = h.after_marshal(d)
        return d

    def _validate(self, raise_errors=True):
        # type: (Callable) -> None
        errors = []
        d = self
        h = d._hooks or type(d)._hooks
        if (h is not None) and (h.before_validate is not None):
            d = h.before_validate(d)
        m = serial.meta.read(d)
        if m is None:
            value_types = None
        else:
            value_types = m.value_types
        if value_types is not None:
            for k, v in d.items():
                errors.extend(validate(v, value_types, raise_errors=False))
        if (h is not None) and (h.after_validate is not None):
            h.after_validate(d)
        if raise_errors and errors:
            raise serial.errors.ValidationError('\n'.join(errors))
        return errors

    def __repr__(self):
        representation = [
            qualified_name(type(self)) + '('
        ]
        items = tuple(self.items())
        if len(items) > 0:
            representation.append('    [')
            for k, v in items:
                rv = (
                    qualified_name(v) if isinstance(v, type) else
                    repr(v)
                )
                rvls = rv.split('\n')
                if len(rvls) > 1:
                    rvs = [rvls[0]]
                    for rvl in rvls[1:]:
                        rvs.append('            ' + rvl)
                    # rvs.append('            ' + rvs[-1])
                    rv = '\n'.join(rvs)
                    representation += [
                        '        (',
                        '            %s,' % repr(k),
                        '            %s' % rv,
                        '        ),'
                    ]
                else:
                    representation.append(
                        '        (%s, %s),' % (repr(k), rv)
                    )
            representation[-1] = representation[-1][:-1]
            representation.append(
                '    ]'
                if self._meta is None or self._meta.value_types is None else
                '    ],'
            )
        cm = serial.meta.read(type(self))
        im = serial.meta.read(self)
        if cm is not im:
            if self._meta.value_types:
                representation.append(
                    '    value_types=(',
                )
                for vt in im.value_types:
                    rv = (
                        qualified_name(vt) if isinstance(vt, type) else
                        repr(vt)
                    )
                    rvls = rv.split('\n')
                    if len(rvls) > 1:
                        rvs = [rvls[0]]
                        rvs += [
                            '        ' + rvl
                            for rvl in rvls[1:]
                        ]
                        rv = '\n'.join(rvs)
                    representation.append('        %s,' % rv)
                if len(self._meta.value_types) > 1:
                    representation[-1] = representation[-1][:-1]
                representation.append('    )')
        representation.append(')')
        if len(representation) > 2:
            return '\n'.join(representation)
        else:
            return ''.join(representation)

    def __eq__(self, other):
        # type: (Any) -> bool
        if type(self) is not type(other):
            return False
        keys = tuple(self.keys())
        other_keys = tuple(other.keys())
        if keys != other_keys:
            return False
        for k in keys:
            if self[k] != other[k]:
                return False
        return True

    def __ne__(self, other):
        # type: (Any) -> bool
        if self == other:
            return False
        else:
            return True

    def __str__(self):
        return serialize(self)


def from_meta(name, metadata, module=None, docstring=None):
    # type: (serial.meta.Meta, str, Optional[str]) -> type
    """
    Constructs an `Object`, `Array`, or `Dictionary` sub-class from an instance of `serial.meta.Meta`.

    Arguments:

        - name (str): The name of the class.

        - class_meta (serial.meta.Meta)

        - module (str): Specify the value for the class definition's `__module__` property. The invoking module will be
          used if this is not specified (if possible).

        - docstring (str): A docstring to associate with the class definition.
    """

    def typing_from_property(p):
        # type: (serial.properties.Property) -> str
        if isinstance(p, type):
            type_hint = p.__name__
        elif isinstance(p, serial.properties.DateTime):
            type_hint = 'datetime'
        elif isinstance(p, serial.properties.Date):
            type_hint = 'date'
        elif isinstance(p, serial.properties.Bytes):
            type_hint = 'bytes'
        elif isinstance(p, serial.properties.Integer):
            type_hint = 'int'
        elif isinstance(p, serial.properties.Number):
            type_hint = Number.__name__
        elif isinstance(p, serial.properties.Boolean):
            type_hint = 'bool'
        elif isinstance(p, serial.properties.String):
            type_hint = 'str'
        elif isinstance(p, serial.properties.Array):
            item_types = None
            if p.item_types:
                if len(p.item_types) > 1:
                    item_types = 'Union[%s]' % (
                        ', '.join(
                           typing_from_property(it)
                           for it in p.item_types
                        )
                    )
                else:
                    item_types = typing_from_property(p.item_types[0])
            type_hint = 'typing.Sequence' + (
                '[%s]' % item_types
                if item_types else
                ''
            )
        elif isinstance(p, serial.properties.Dictionary):
            value_types = None
            if p.value_types:
                if len(p.value_types) > 1:
                    value_types = 'Union[%s]' % (
                        ', '.join(
                           typing_from_property(vt)
                           for vt in p.value_types
                        )
                    )
                else:
                    value_types = typing_from_property(p.value_types[0])
            type_hint = (
                'Dict[str, %s]' % value_types
                if value_types else
                'dict'
            )
        elif p.types:
            if len(p.types) > 1:
                type_hint = 'Union[%s]' % ', '.join(
                    typing_from_property(t) for t in p.types
                )
            else:
                type_hint = typing_from_property(p.types[0])
        else:
            type_hint = 'Any'
        return type_hint
    if docstring is not None:
        if '\t' in docstring:
            docstring = docstring.replace('\t', '    ')
        lines = docstring.split('\n')
        indentation_length = float('inf')
        for line in lines:
            match = re.match(r'^[ ]+', line)
            if match:
                indentation_length = min(
                    indentation_length,
                    len(match.group())
                )
            else:
                indentation_length = 0
                break
        wrapped_lines = []
        for line in lines:
            line = '    ' + line[indentation_length:]
            if len(line) > 120:
                indent = re.match(r'^[ ]*', line).group()
                li = len(indent)
                words = re.split(r'([\w]*[\w,/"\',.;\-?`])', line[li:])
                wrapped_line = ''
                for word in words:
                    if (len(wrapped_line) + len(word) + li) <= 120:
                        wrapped_line += word
                    else:
                        wrapped_lines.append(indent + wrapped_line)
                        wrapped_line = '' if not word.strip() else word
                if wrapped_line:
                    wrapped_lines.append(indent + wrapped_line)
            else:
                wrapped_lines.append(line)
        docstring = '\n'.join(
            ['    """'] +
            wrapped_lines +
            ['    """']
        )
    if isinstance(metadata, serial.meta.Dictionary):
        out = [
            'class %s(serial.model.Dictionary):' % name
        ]
        if docstring is not None:
            out.append(docstring)
        out.append('\n    pass')
    elif isinstance(metadata, serial.meta.Array):
        out = [
            'class %s(serial.model.Array):' % name
        ]
        if docstring is not None:
            out.append(docstring)
        out.append('\n    pass')
    elif isinstance(metadata, serial.meta.Object):
        out = [
            'class %s(serial.model.Object):' % name
        ]
        if docstring is not None:
            out.append(docstring)
        out += [
            '',
            '    def __init__(',
            '        self,',
            '        _=None,  # type: Optional[Union[str, bytes, dict, typing.Sequence, IO]]'
        ]
        for n, p in metadata.properties.items():
            out.append(
                '        %s=None,  # type: Optional[%s]' % (n, typing_from_property(p))
            )
        out.append(
            '    ):'
        )
        for n in metadata.properties.keys():
            out.append(
                '        self.%s = %s' % (n, n)
            )
        out.append('        super().__init__(_)\n\n')
    else:
        raise ValueError(metadata)
    class_definition = '\n'.join(out)
    namespace = dict(__name__='from_meta_%s' % name)
    imports = '\n'.join([
        'from __future__ import nested_scopes, generators, division, absolute_import, with_statement, \\',
        'print_function, unicode_literals',
        'from future import standard_library',
        'standard_library.install_aliases()',
        'from builtins import *',
        'try:',
        '    import typing',
        '    from typing import Union, Dict, Any',
        'except ImportError:',
        '    typing = Union = Any = None',
        'import serial\n'
    ])
    exec('%s\n\n%s' % (imports, class_definition), namespace)
    result = namespace[name]
    result._source = class_definition
    if module is None:
        try:
            module = sys._getframe(1).f_globals.get('__name__', '__main__')
        except (AttributeError, ValueError):
            pass
    if module is not None:
        result.__module__ = module
    result._meta = metadata
    return result