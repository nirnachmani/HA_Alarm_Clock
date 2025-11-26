"""Storage handling for HA Alarm Clock."""
from __future__ import annotations
from typing import Dict, Any, MutableMapping, Optional, cast
import logging
import asyncio

from homeassistant.core import HomeAssistant, callback
from homeassistant.loader import bind_hass
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

DATA_REGISTRY = "ha_alarm_clock_storage"
STORAGE_KEY = "ha_alarm_clock.storage"
STORAGE_VERSION = 1
SAVE_DELAY = 1  # debounce seconds


class AlarmReminderStorage:
    """Simple storage for alarms & reminders (id -> item dict)."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        # keep a single flattened in-memory mapping for runtime convenience
        # but persist as separated buckets "Alarms"/"Reminders" per request
        self._items: MutableMapping[str, Dict[str, Any]] = {}
        self._save_handle: Optional[asyncio.TimerHandle] = None
        self._lock = asyncio.Lock()

    async def async_load(self) -> Dict[str, Dict[str, Any]]:
        """Load all items from storage and return flattened mapping item_id -> item dict.

        Supports both legacy format ({"items": {...}}) and new grouped format:
        {
          "version": 1,
          "minor_version": 1,
          "key": "ha_alarm_clock.storage",
          "data": {
            "Alarms": {...},
            "Reminders": {...}
          }
        }
        """
        data = await self._store.async_load()
        if not data:
            self._items = {}
            return {}

        # New grouped format: try to read from top-level "data" key
        if isinstance(data, dict) and "data" in data:
            grouped = data.get("data", {}) or {}
            alarms = grouped.get("Alarms", {}) or {}
            reminders = grouped.get("Reminders", {}) or {}
            merged: Dict[str, Dict[str, Any]] = {}
            merged.update(alarms)
            merged.update(reminders)
            # Keep in-memory flattened mapping for runtime operations
            self._items = dict(merged)
            _LOGGER.debug("AlarmReminderStorage loaded grouped format: %d alarms + %d reminders",
                          len(alarms), len(reminders))
            return dict(self._items)

        # Legacy format (compat): {"items": {...}}
        raw = data.get("items") if isinstance(data, dict) else None
        if not raw:
            self._items = {}
            return {}
        self._items = dict(raw)
        _LOGGER.debug("AlarmReminderStorage loaded legacy format: %d items", len(self._items))
        return dict(self._items)


    @callback
    def async_schedule_save(self) -> None:
        """Schedule save with debounce (SAVE_DELAY sec)."""
        # cancel existing handle if present
        if self._save_handle:
            try:
                self._save_handle.cancel()
            except Exception:
                pass
            self._save_handle = None

        loop = self.hass.loop
        self._save_handle = loop.call_later(SAVE_DELAY, lambda: self.hass.async_create_task(self.async_save()))

    async def async_save(self, items: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Persist flattened items mapping to storage using grouped structure.

        The file will contain top-level metadata and 'data' with 'Alarms' and
        'Reminders' buckets as requested.
        """
        try:
            async with self._lock:
                await self._save_locked(items)
        except Exception as err:
            _LOGGER.exception("Error saving to storage: %s", err)

    async def _save_locked(self, items: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Persist items to storage; caller must hold _lock."""
        if items is None:
            items = dict(self._items)

        alarms: Dict[str, Dict[str, Any]] = {}
        reminders: Dict[str, Dict[str, Any]] = {}
        for item_id, data in items.items():
            stored = dict(data)
            sched = stored.get("scheduled_time")
            try:
                from datetime import datetime
                if isinstance(sched, datetime):
                    stored["scheduled_time"] = sched.isoformat()
                canonical = stored.get("scheduled_time_canonical")
                if isinstance(canonical, datetime):
                    stored["scheduled_time_canonical"] = canonical.isoformat()
            except Exception:
                pass
            if stored.get("is_alarm"):
                alarms[item_id] = stored
            else:
                reminders[item_id] = stored

        payload = {
            "version": STORAGE_VERSION,
            "minor_version": 1,
            "key": STORAGE_KEY,
            "data": {
                "Alarms": alarms,
                "Reminders": reminders,
            },
        }

        await self._store.async_save(payload)
        merged = {}
        merged.update(alarms)
        merged.update(reminders)
        self._items = dict(merged)
        _LOGGER.debug(
            "AlarmReminderStorage saved: %d alarms + %d reminders",
            len(alarms),
            len(reminders),
        )

    @callback
    def async_get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Return item by id (in-memory)."""
        return dict(self._items.get(item_id)) if item_id in self._items else None

    async def async_create_item(self, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new item and persist."""
        async with self._lock:
            self._items[item_id] = dict(data)
            await self._save_locked(self._items)
            return dict(self._items[item_id])

    async def async_update_item(self, item_id: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing item and persist."""
        async with self._lock:
            if item_id not in self._items:
                return None
            self._items[item_id].update(changes)
            await self._save_locked(self._items)
            return dict(self._items[item_id])

    async def async_delete_item(self, item_id: str) -> bool:
        """Delete an item and persist."""
        async with self._lock:
            if item_id in self._items:
                del self._items[item_id]
                await self._save_locked(self._items)
                return True
            return False


@bind_hass
async def async_get_storage(hass: HomeAssistant) -> AlarmReminderStorage:
    """Return (and initialize) AlarmReminderStorage for hass."""
    task = hass.data.get(DATA_REGISTRY)
    if task is None:

        async def _load_reg() -> AlarmReminderStorage:
            reg = AlarmReminderStorage(hass)
            # load existing items into memory
            await reg.async_load()
            return reg

        task = hass.data[DATA_REGISTRY] = hass.async_create_task(_load_reg())

    return cast(AlarmReminderStorage, await task)
