import logging
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry for managing classes.

    Can be subclassed to create specific registries for different types.
    Each subclass will have its own separate registry storage.
    """

    _items: dict[str, type[T]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._items = {}

    def __init__(self):
        raise TypeError(f"{self.__class__.__name__} is a static class and cannot be instantiated")

    @classmethod
    def register(cls, item_class: type[T], name: str | None = None) -> None:
        """Register an item class.

        Args:
            item_class: Class to register
            name: Optional name to register the class under
        """
        if item_class.__name__ in cls._items:
            return

        cls._items[item_class.__name__.lower()] = item_class
        if name is not None:
            cls._items[name.lower()] = item_class

    @classmethod
    def get(cls, name: str) -> type[T] | None:
        """Get a class by name.

        Args:
            name: Name of the class to retrieve

        Returns:
            Class or None if not found
        """
        return cls._items.get(name.lower())

    @classmethod
    def list_items(cls) -> list[type[T]]:
        """Get all registered items.

        Returns:
            List of classes
        """
        return list(set(cls._items.values()))

    @classmethod
    def resolve(cls, names: list[str]) -> list[type[T]]:
        """Resolve names to classes.

        Args:
            names: List of names to resolve

        Returns:
            List of classes
        """
        items = []
        for name in names:
            if item_class := cls._items.get(name.lower()):
                items.append(item_class)
            else:
                logger.warning(f"Item {name} not found in {cls.__name__}")
                continue
        return items

    @classmethod
    def clear(cls) -> None:
        """Clear all registered items."""
        cls._items.clear()


class AgentRegistry(Registry["BaseAgent"]):
    pass


class ToolRegistry(Registry["BaseTool"]):
    pass
