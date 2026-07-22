from __future__ import annotations

from copy import deepcopy

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Slot


class ObjectListModel(QAbstractListModel):
    """Modelo de diccionarios con roles estables, apropiado para QML."""

    countChanged = Signal()

    def __init__(self, roles: list[str], parent=None):
        super().__init__(parent)
        self._roles = tuple(roles)
        self._role_ids = {Qt.UserRole + index + 1: role for index, role in enumerate(roles)}
        self._items: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        key = self._role_ids.get(role)
        return self._items[index.row()].get(key) if key else None

    def roleNames(self):
        return {role: name.encode("utf-8") for role, name in self._role_ids.items()}

    def replace(self, items: list[dict]):
        self.beginResetModel()
        self._items = [deepcopy(item) for item in items]
        self.endResetModel()
        self.countChanged.emit()

    def append(self, item: dict):
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(deepcopy(item))
        self.endInsertRows()
        self.countChanged.emit()

    def update_item(self, row: int, updates: dict):
        if not 0 <= row < len(self._items):
            return
        self._items[row].update(deepcopy(updates))
        idx = self.index(row, 0)
        roles = [role for role, name in self._role_ids.items() if name in updates]
        self.dataChanged.emit(idx, idx, roles)

    def remove(self, row: int):
        if not 0 <= row < len(self._items):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self.countChanged.emit()

    def clear(self):
        self.replace([])

    def item(self, row: int) -> dict | None:
        if 0 <= row < len(self._items):
            return deepcopy(self._items[row])
        return None

    def items(self) -> list[dict]:
        return deepcopy(self._items)

    @Slot(int, result="QVariantMap")
    def get(self, row: int):
        return self.item(row) or {}

    @Slot(result=int)
    def count(self):
        return len(self._items)
