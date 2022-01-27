from __future__ import annotations

import abc
import collections
import functools
import math
from typing import Type

from netcast.cast.serializer import Serializer, Constraint, ConstraintError
from netcast.toolkit import strings
from netcast.toolkit.symbol import Symbol

bounds = collections.namedtuple('bounds', 'min_val max_val')


class IntConstraint(Constraint):
    def validate_load(self, load):
        min_val, max_val = self.cfg.min_val, self.cfg.max_val
        if min_val <= load <= max_val:
            return load
        min_val, max_val = map(
            functools.partial(strings.truncate, stats=None),
            map(str, (min_val, max_val))
        )
        raise ConstraintError(
            f'loaded object is out of serialization bounds [{min_val}, {max_val}]'
        )


class Primitive(Serializer, abc.ABC):
    """Base class for all Python primitive types."""
    __load_type__ = Symbol('Primitive')
    new_context = True


class BaseInt(Primitive, abc.ABC):
    """Base integer """
    __load_type__ = int
    bit_length = math.inf
    bounds = (-math.inf, math.inf)

    @classmethod
    def sizeof(cls):
        if math.inf in cls.bounds or -math.inf in cls.bounds:
            return math.inf
        return cls.bit_length // 8


class UnsignedBaseInt(BaseInt, abc.ABC):
    bounds = bounds(0, math.inf)
    constraints = (IntConstraint(**bounds._asdict()),)


@functools.lru_cache
def _factorize_constraint(bit_length, signed=True):
    if bit_length:
        pow2 = 2 ** bit_length
        if signed:
            pow2 //= 2
            min_val, max_val = -pow2, pow2 - 1
        else:
            min_val, max_val = 0, pow2 - 1
        constraint_bounds = bounds(min_val, max_val)
    elif signed:
        constraint_bounds = BaseInt.bounds
        bit_length = math.inf
    else:
        constraint_bounds = UnsignedBaseInt.bounds
        bit_length = math.inf
    return IntConstraint(bit_length=bit_length, **constraint_bounds._asdict())


def _get_int_serializer_name(size, signed=True) -> str:
    name = 'Signed' if signed else ''
    name += 'Int'
    if size:
        name += str(size)
    return name


def int_serializer(bit_length, signed=True) -> Type[BaseInt] | type:
    constraint = _factorize_constraint(bit_length, signed=signed)
    name = _get_int_serializer_name(bit_length, signed=signed)
    serializer = type(name, (BaseInt, abc.ABC), {'constraints': (constraint,)})
    serializer.bounds = bounds(constraint.cfg.min_val, constraint.cfg.max_val)
    serializer.bit_length = constraint.cfg.bit_length
    return serializer


Bool = Bit = int_serializer(1, signed=False)
Nibble = HalfByte = Tetrade = int_serializer(4, signed=False)

SignedBaseInt = BaseInt
SignedInt8 = Int8 = int_serializer(8)
SignedInt16 = Int16 = int_serializer(16)
SignedInt32 = Int32 = int_serializer(32)
SignedInt64 = Int64 = int_serializer(64)
SignedInt128 = Int128 = int_serializer(128)
SignedInt256 = Int256 = int_serializer(256)
SignedInt512 = Int512 = int_serializer(512)

UnsignedInt8 = int_serializer(8, signed=False)
UnsignedInt16 = int_serializer(16, signed=False)
UnsignedInt32 = int_serializer(32, signed=False)
UnsignedInt64 = int_serializer(64, signed=False)
UnsignedInt128 = int_serializer(128, signed=False)
UnsignedInt256 = int_serializer(256, signed=False)
UnsignedInt512 = int_serializer(512, signed=False)

# aliases
Byte = SignedByte = Char = SignedChar = SignedInt8
UnsignedByte = UnsignedChar = UnsignedInt8

Short = ShortInt = Int16
Int = Long = LongInt = Int32
Signed = SignedInt = SignedLong = SignedLongInt = Int32
Unsigned = UnsignedInt = UnsignedLong = UnsignedLongInt = UnsignedInt32
LongLong = SignedLongLong = SignedLongLongInt = Int64
UnsignedLongLong = UnsignedLongLongInt = UnsignedInt64
