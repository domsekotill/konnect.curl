# Copyright 2023-2024  Dom Sekotill <dom.sekotill@kodo.org.uk>

"""
Scalar quantities, which have a magnitude and a unit

Defining Units
--------------

Unit types for `Quantity` are created by subclassing the `QuantityUnit` `enum` base:

>>> class Time(QuantityUnit):
...     MILLISECONDS = 1
...     SECONDS = 1000
...     MINUTES = 60 * SECONDS

>>> class Distance(QuantityUnit):
...     MILLIMETERS = 1
...     CENTIMETERS = 10 * MILLIMETERS
...     METERS = 100 * CENTIMETERS
...     KILOMETERS = 1000 * METERS
...     INCH = 24 * MILLIMETERS
...     HALF_INCH = INCH // 2  # Hey! Hands off
...     QUARTER_INCH = INCH // 4

The enum members form units of relative size to each other. They MUST be integers so
typically the smallest (highest precision) unit is `1` and the others are some multiple of
it. Note that the designated 'unit' can be changed without breaking dependant code (as long
as the code is using the quantities right).  In this case the unitary value is 0.5mm:

>>> class Distance(QuantityUnit):
...     MILLIMETERS = 2  # Scaled to allow SIXTEENTH_INCH to be an integer
...     CENTIMETERS = 10 * MILLIMETERS
...     METERS = 100 * CENTIMETERS
...     KILOMETERS = 1000 * METERS
...     INCH = 24 * MILLIMETERS
...     # ...
...     SIXTEENTH_INCH = INCH // 16  # 1/16″ is 1.5mm


Creating Scalar Quantities
--------------------------

A scalar quantity can be created using the matrix multiplication operator "@" with a
scalar unit, e.g. 2 seconds:

>>> quantity: Quantity[Time] = 2 @ Time.SECONDS

Units of the same type relate to one another as you would expect (parentheses for clarity):

>>> assert (2 @ Time.SECONDS) == (2000 @ Time.MILLISECONDS)

Quantities may also be multiplied (and divided) by unitless values:

>>> ONE_SECOND = 1 @ Time.SECONDS
>>> assert (ONE_SECOND / 2) == (500 @ Time.MILLISECONDS)

Note that quantities are really just integers which, at runtime, have no additional
information attached to them. This means that Python will happily accept any `Quantity`
wherever it would accept an integer; however static type checkers such as MyPy will complain
about it, which is good as it is almost certainly a mistake to attempt to, for example, sum
time and distance quantities, or sum a quantity with an arbitrary value:

>>> meaningless_value = (2 @ Time.SECONDS) + (10 @ Distance.MILLIMETERS)

>>> # Depending on the declaration of Distance, 100 here could be 100mm or 100/16″,
... # or anything else...
... unreliable_value = (2 @ Distance.METERS) + 100

Multiplying quantities with other quantities, even of the same type, would produce
a different unit, which is not supported.  (However, it is not inconceivable that it could
be supported in the future.) The following will also fail static type checks:

>>> area = (2 @ Distance.METERS) * (2 @ Distance.METERS)  # 4.0m²
>>> speed = (100 @ Distance.METERS) / (1 @ Time.SECOND)  # 100m/s


Using Scalar Quantities
-----------------------

At some point quantities will need to be passed through an interface of some sort where the
unit information will be lost.  Such interfaces will define a single unit they accept; for
instance `time.sleep()` requires an argument in seconds.  Upon reaching such an interface,
quantities can be stripped of their scalar types and converted to the required unit with the
right bit-shift operator ">>" or integer division operator "//":

>>> delay = 2 @ Time.MINUTES
>>> ...
>>> time.sleep(delay >> Time.SECONDS)

With the ">>" operator the type of the resulting value is always a `float` and
will only be precise up to the highest precision unit for a defined `QuantityUnit` type (the
unit with a magnitude of `1`, which need not be explicitly defined).

With the "//" operator the resulting type will be `int`, with whatever loss of precision
that implies.


Choice of Operators
-------------------

The operators for constructing ("@") and deconstructing (">>") quantities may seem
a bit odd, given that what they actually do is multiply and divide the values.
They were chosen to be visually distinct from other multiplication and division operations
on quantities and scalar units.

The matrix multiplication operator therefore replaces the scalar multiplication operator,
while the shift operator, which looks arrow-like, is used to convert to the indicated
unit.

>>> # As in ...
... # quantity  (converted to)  units
... time              >>        Time.SECONDS
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING
from typing import Generic
from typing import Self
from typing import TypeVar
from typing import overload

U = TypeVar("U", bound="QuantityUnit")


class Quantity(int, Generic[U]):
	"""
	A scalar quantity of a given type 'U'
	"""

	if TYPE_CHECKING:

		@overload
		def __add__(self, other: Quantity[U]) -> Quantity[U]: ...

		@overload
		def __add__(self, other: int) -> int: ...

		def __add__(self, other: int) -> int:
			"""
			Adding two quantities creates a new quantity
			"""
			...

		@overload
		def __sub__(self, other: Quantity[U]) -> Quantity[U]: ...

		@overload
		def __sub__(self, other: int) -> int: ...

		def __sub__(self, other: int) -> int:
			"""
			Subtracting a quantity from another creates a new quantity
			"""
			...

		def __mul__(self, other: int|float) -> Quantity[U]:
			"""
			Quantities can be multiplied by unitless values to produce a new quantity
			"""
			...

		def __truediv__(self, other: int|float) -> Quantity[U]:
			"""
			Quantities can be divided by unitless values to produce a new quantity
			"""
			...


class QuantityUnit(enum.Enum):
	"""
	Enum base class for units
	"""

	if TYPE_CHECKING:
		@property
		def value(self) -> int: ...  # noqa: D102

	def __rmatmul__(self, scalar: float|int) -> Quantity[Self]:
		return Quantity(self.value * scalar)

	def __rrshift__(self, quantity: Quantity[Self]) -> float:
		return quantity / self.value

	def __rfloordiv__(self, quantity: Quantity[Self]) -> int:
		return quantity // self.value
