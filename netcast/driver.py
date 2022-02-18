from __future__ import annotations  # Python 3.8

import functools
import inspect
import sys
from typing import ClassVar, Type, TypeVar, TYPE_CHECKING

from netcast import serializers
from netcast.exceptions import NetcastError
from netcast.serializer import Serializer


if TYPE_CHECKING:
    from netcast.serializers import ModelSerializer
    from netcast.model import Model  # noqa: F401


__all__ = (
    "Driver",
    "DriverMeta",
    "serializer",
    "interface"
)

ORIGIN_FIELD = "__netcast_origin__"


_M = TypeVar("_M", bound="Model")


class DriverMeta(type):
    @functools.singledispatchmethod
    def get_model_serializer(cls, model_serializer, /, components=(), settings=None):
        if settings is None:
            settings = {}
        if model_serializer is None:
            model_serializer = cls.default_model_serializer
        return model_serializer(*components, **settings)

    def lookup(cls, serializer_type):
        try:
            return cls._lookup_dict[serializer_type]
        except KeyError:
            return NotImplemented

    def __getattr__(cls, item):
        alias = getattr(serializers, item, None)
        if alias is None or not issubclass(alias, Serializer):
            raise AttributeError(item)
        return object.__getattribute__(cls, alias.__name__)

    def __call__(
            self,
            model: _M = None,
            return_serializer=True,
            **settings
    ) -> ModelSerializer:
        if return_serializer:
            if model is None:
                raise ValueError("`Model` type or instance expected")
            if isinstance(model, type):
                model = model()
            return model.resolve_serializer(self, settings)
        return super().__call__()


class Driver(metaclass=DriverMeta):
    __drivers_registry__: dict[str, Driver] = {}
    _lookup_dict: ClassVar[dict[Type[Serializer], Type[Serializer]]]

    default_model_serializer = None

    def __init_subclass__(cls, driver_name=None, config=False):
        if config:
            return

        if driver_name is None:
            driver_name = cls._conjure_driver_name(stack_level=2)

        if driver_name in Driver.__drivers_registry__:
            raise ValueError(f"{driver_name!r} driver has already been implemented")

        cls.name = driver_name
        cls.__drivers_registry__[driver_name] = cls
        cls._lookup_dict = {}

        for _, member in inspect.getmembers(cls, _is_impl):
            cls.register(member)

        cls.DEBUG = __debug__

    @staticmethod
    def _conjure_driver_name(stack_level=1):
        f_globals = inspect.stack()[stack_level][0].f_globals
        driver_name = f_globals.get("DRIVER_NAME", f_globals.get("__name__"))
        if driver_name is None:
            raise ValueError("driver name is required")
        return sys.intern(driver_name)

    @classmethod
    def register(cls, member):
        link_to = getattr(member, "__netcast_origin__", member.__base__)
        cls._lookup_dict[link_to] = member


def _is_impl(member):
    return isinstance(member, type) and issubclass(member, Serializer)


def serializer(interface_class, serializer_class=None, origin=None):
    if serializer_class is None:
        raise NetcastError("no serializer has been set on this adapter")
    impl = type(
        serializer_class.__name__,
        (serializer_class, interface_class),
        {ORIGIN_FIELD: (serializer_class if origin is None else origin)},
    )
    return impl


def interface(interface_class, origin=None):
    if origin is None:
        origin = getattr(interface_class, ORIGIN_FIELD, None)
    return functools.partial(serializer, interface_class, origin=origin)
