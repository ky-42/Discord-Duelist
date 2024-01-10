from typing import ClassVar, Dict, Protocol


class IsDataclass(Protocol):
    """Protocol for checking if a class is a dataclass.

    Used to make sure paramters passed to functions are dataclasses.
    """

    __dataclass_fields__: ClassVar[Dict]
