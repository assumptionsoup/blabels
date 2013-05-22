'''
*******************************************************************************
    License and Copyright
    Copyright 2012-2013 Jordan Hueckstaedt
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# import inspect
import functools
from collections import defaultdict


class RegisterObject(object):
    '''
    Base class to which all Registers for the RegisteringType metaclass should derrive.
    This is an interface class, not a fully implemented class.
    '''
    register_name = 'RegisterObject'
    register_vals = ((), {})


class RegisterDescriptor(RegisterObject):
    '''
    A descriptor which can register a method on a class which uses the
    metaclass RegisteryingType.

    Method names will be stored on the parent class in an attribute
    named from this class' register_name attribute. By convention,
    register_name should be named after this class.

    Example
    -------
    >>> class MyClass(object):
    >>>     __metaclass__ = RegisteringType
    >>>
    >>>     @RegisterDescriptor
    >>>     def my_method(self):
    >>>         print "I'm a method!"
    >>>
    >>> print MyClass.RegisterDescriptor
    {'my_method': ((), {})}
    '''

    register_name = 'RegisterDescriptor'

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func

    def __get__(self, inst, instType=None):
        if inst is None:
            return self
        newfunc = self.func.__get__(inst, instType)
        return self.__class__(newfunc)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class CachedRegister(RegisterDescriptor):
    '''
    A descriptor which can register and cache a method on a class which
    uses the metaclass RegisteryingType.

    Method names will be stored on the parent class in an attribute
    named from this class' register_name attribute. By convention,
    register_name should be named after this class.

    Example
    -------
    >>> class MyClass(object):
    >>>     __metaclass__ = RegisteringType
    >>>
    >>>     @CachedRegister
    >>>     def my_method(self):
    >>>         print "I'm a method!"
    >>>         return 'Yes'
    >>>
    >>> print MyClass.CachedRegister
    {'my_method': ((), {})}
    >>> myClass = MyClass()
    >>> myClass.my_method
    # I'm a method!
    'Yes'
    >>> myClass.my_method
    'Yes'
    >>> del myClass.my_method  # uncache
    >>> myClass.my_method
    # I'm a method!
    'Yes'
    '''

    register_name = 'CachedRegister'

    def __get__(self, instance, instanceType=None):
        if instance is None:
            return self

        value = self.func(instance)
        setattr(instance, self.__name__, value)
        return value


class RegisterDecorator(RegisterObject):
    '''
    A decorator which can register a method on a class which uses the
    metaclass RegisteryingType.

    Arguments passed to this decorator will be stored on the parent
    class in an attribute named from this class' register_name
    attribute. By convention, register_name should be named after this
    class.

    Example
    -------
    >>> class MyClass(object):
    >>>     __metaclass__ = RegisteringType
    >>>
    >>>     @RegisterDecorator('hello', default=True)
    >>>     def my_method(self):
    >>>         print "I'm a method!"
    >>>
    >>> print MyClass.RegisterDecorator
    {'my_method': (('hello',), {'default': True})}
    '''

    # By convention, register_name is the name of the class.
    register_name = 'RegisterDecorator'

    def __init__(self, *args, **kwargs):
        self.register_vals = (args, kwargs)

    def __call__(self, func):
        func.register_vals = self.register_vals
        func.register_name = self.register_name
        return func


class RegisteringType(type):
    '''
    Finds RegisterObject's on class creation and stores their
    information in a dict.

    Information is stored in a dict based on the RegisterObject's
    register_name attribute, which by convention should be the
    RegisterObject's class name.

    RegisterObjects are found by the existence of the register_name and
    register_vals attribute.

    Example
    -------
    >>> class MyClass(object):
    >>>     __metaclass__ = RegisteringType
    >>>
    >>>     @RegisterDecorator('hello', default=True)
    >>>     def my_method(self):
    >>>         print "I'm a method!"
    >>>
    >>> print MyClass.RegisterDecorator
    {'my_method': (('hello',), {'default': True})}
    '''

    def __new__(mcl, name, bases, attrs):
        register_dict = defaultdict(dict)
        for method, val in attrs.items():
            try:
                register_name = val.register_name
                val.register_vals
            except AttributeError:
                continue

            register_dict[register_name].update({method: val.register_vals})

        for register_name in register_dict:
            for base in bases:
                inherited_register = getattr(base, register_name, {}).copy()
                inherited_register.update(register_dict[register_name])
                register_dict[register_name] = inherited_register

            attrs[register_name] = register_dict[register_name]
        cls = super(RegisteringType, mcl).__new__(mcl, name, bases, attrs)
        return cls


class CachedMethod(object):
    def __init__(self, wrapped_func):
        # Make self look like calculate_function
        # (also caches everything we need to work)
        functools.update_wrapper(self, wrapped_func)

    def __get__(self, instance, instanceType=None):
        if instance is None:
            return self

        value = self.__wrapped__(instance)
        setattr(instance, self.__name__, value)
        return value


def compound_decorator(*decs):
    '''Compound several decorators into one'''

    def deco(orig_func):
        for dec in reversed(decs):
            orig_func = dec(orig_func)
        return orig_func
    return deco
