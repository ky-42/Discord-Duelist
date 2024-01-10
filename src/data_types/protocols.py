"""Contains protocols for type checking"""

from typing import ClassVar, Dict, Protocol


class IsDataclass(Protocol):
    """Protocol for checking if a class is a dataclass.

    Used to make sure parameters passed to functions are dataclasses.
    """

    __dataclass_fields__: ClassVar[Dict]
