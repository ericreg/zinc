"""Symbol table and scope management for the Zinc compiler."""

from typing import NamedTuple, Optional

from .types import BaseType, TypeInfo


class Symbol(NamedTuple):
    """A symbol in the symbol table."""

    name: str
    type_info: TypeInfo

    def __repr__(self):
        return f"Symbol(name={self.name}, type={self.type_info.base})"


class Scope:
    """A scope in the symbol table, supporting nested scopes."""

    def __init__(self, parent: Optional["Scope"] = None):
        self.parent = parent
        self._symbols: dict[str, Symbol] = {}
        self.children: list["Scope"] = []
        self.function = None  # For function scope tracking

    def define(self, name: str, type_info: TypeInfo) -> Symbol:
        """Define a new symbol in this scope."""
        sym = Symbol(name=name, type_info=type_info)
        self._symbols[name] = sym
        return sym

    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol by name, searching parent scopes."""
        if name in self._symbols:
            return self._symbols[name]
        elif self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up a symbol only in the current scope."""
        return self._symbols.get(name)

    def enter_scope(self) -> "Scope":
        """Create and enter a new child scope."""
        child = Scope(parent=self)
        self.children.append(child)
        return child

    def exit_scope(self) -> "Scope":
        """Exit to the parent scope."""
        if self.parent is None:
            raise RuntimeError("Cannot exit the global scope")
        return self.parent

    def add_symbol(self, symbol: Symbol) -> None:
        """Add an existing symbol to this scope (legacy support)."""
        self._symbols[symbol.name] = symbol
