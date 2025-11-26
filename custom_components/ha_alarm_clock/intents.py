"""Intent handling for HA Alarm Clock."""
from __future__ import annotations

import logging
from datetime import datetime

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import dt as dt_util

from .const import (
    CONF_MEDIA_PLAYER,
    DOMAIN,
    SERVICE_SET_ALARM,
    SERVICE_SET_REMINDER,
    SERVICE_SNOOZE_ALARM,
    SERVICE_SNOOZE_REMINDER,
)

_LOGGER = logging.getLogger(__name__)


def _resolve_coordinator(hass: HomeAssistant):
    """Return the shared coordinator instance if available."""
    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict):
        return None

    coordinator = domain_data.get("coordinator")
    if coordinator:
        return coordinator

    for data in domain_data.values():
        if isinstance(data, dict) and data.get("coordinator"):
            return data["coordinator"]

    return None


def _resolve_default_media_player(hass: HomeAssistant) -> str | None:
    """Return the configured default media player for intents."""
    entries = hass.config_entries.async_entries(DOMAIN)
    for entry in entries:
        media_player = entry.options.get(CONF_MEDIA_PLAYER)
        if media_player:
            return media_player
    return None


def _parse_slot_datetime(value: str) -> datetime | None:
    """Parse a datetime value supplied by Assist intent slots."""
    if not value:
        return None

    dt_value = dt_util.parse_datetime(value)
    if dt_value is None:
        try:
            dt_value = datetime.fromisoformat(value)
        except ValueError:
            return None

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=dt_util.UTC)

    return dt_util.as_local(dt_value)


def _find_active_item_id(coordinator, *, is_alarm: bool) -> str | None:
    """Locate the first active alarm or reminder in the coordinator."""
    active_items = getattr(coordinator, "_active_items", {})
    if not isinstance(active_items, dict):
        return None

    for item_id, item in active_items.items():
        if not isinstance(item, dict):
            continue
        if item.get("is_alarm") != is_alarm:
            continue
        if item.get("status") == "active":
            return item_id

    return None

async def async_setup_intents(hass: HomeAssistant) -> None:
    """Set up the HA Alarm Clock intents."""
    if hasattr(hass.data, f"{DOMAIN}_intents_registered"):
        _LOGGER.debug("Intents already registered, skipping setup")
        return

    intent.async_register(hass, SetAlarmIntentHandler())
    intent.async_register(hass, SetReminderIntentHandler())
    intent.async_register(hass, StopAlarmIntentHandler())
    intent.async_register(hass, StopReminderIntentHandler())
    intent.async_register(hass, SnoozeAlarmIntentHandler())
    intent.async_register(hass, SnoozeReminderIntentHandler())

    # Mark intents as registered
    hass.data[f"{DOMAIN}_intents_registered"] = True

class SetAlarmIntentHandler(intent.IntentHandler):
    """Handle SetAlarm intents."""

    intent_type = "SetAlarm"
    slot_schema = {
        vol.Required("datetime"): str,
        vol.Optional("message"): str,
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        datetime_value = slots["datetime"]["value"]
        message = slots.get("message", {}).get("value", "") or ""

        schedule_dt = _parse_slot_datetime(datetime_value)
        if not schedule_dt:
            _LOGGER.warning("SetAlarm intent received unsupported datetime: %s", datetime_value)
            response = intent_obj.create_response()
            response.async_set_speech("I couldn't understand the requested alarm time.")
            return response

        media_player = _resolve_default_media_player(hass)
        if not media_player:
            _LOGGER.warning("SetAlarm intent rejected—no default media player configured")
            response = intent_obj.create_response()
            response.async_set_speech("I need a default media player configured before setting alarms.")
            return response

        service_data = {
            "time": schedule_dt.time().replace(microsecond=0).isoformat(),
            "date": schedule_dt.date().isoformat(),
            "message": message,
            "media_player": media_player,
        }

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_ALARM,
            service_data,
            blocking=True,
        )

        response = intent_obj.create_response()
        response.async_set_speech(
            f"Alarm set for {schedule_dt.strftime('%Y-%m-%d %H:%M')}"
        )
        return response

class SetReminderIntentHandler(intent.IntentHandler):
    """Handle SetReminder intents."""

    intent_type = "SetReminder"
    slot_schema = {
        vol.Required("task"): str,
        vol.Required("datetime"): str,
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        task = slots["task"]["value"]
        datetime_value = slots["datetime"]["value"]

        schedule_dt = _parse_slot_datetime(datetime_value)
        if not schedule_dt:
            _LOGGER.warning("SetReminder intent received unsupported datetime: %s", datetime_value)
            response = intent_obj.create_response()
            response.async_set_speech("I couldn't understand the requested reminder time.")
            return response

        media_player = _resolve_default_media_player(hass)
        if not media_player:
            _LOGGER.warning("SetReminder intent rejected—no default media player configured")
            response = intent_obj.create_response()
            response.async_set_speech("I need a default media player configured before setting reminders.")
            return response

        service_data = {
            "time": schedule_dt.time().replace(microsecond=0).isoformat(),
            "date": schedule_dt.date().isoformat(),
            "name": task,
            "message": task,
            "media_player": media_player,
        }

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_REMINDER,
            service_data,
            blocking=True,
        )

        response = intent_obj.create_response()
        response.async_set_speech(
            f"Reminder set for {schedule_dt.strftime('%Y-%m-%d %H:%M')}: {task}"
        )
        return response

class StopAlarmIntentHandler(intent.IntentHandler):
    """Handle StopAlarm intents."""

    intent_type = "StopAlarm"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        coordinator = _resolve_coordinator(hass)

        if coordinator is None:
            _LOGGER.warning("StopAlarm intent received but coordinator unavailable")
            response = intent_obj.create_response()
            response.async_set_speech("I couldn't reach the alarms system right now.")
            return response

        active_id = _find_active_item_id(coordinator, is_alarm=True)

        if active_id:
            await coordinator.stop_item(active_id, True)
            spoken_message = "Alarm stopped"
        else:
            spoken_message = "There aren't any alarms ringing right now."

        response = intent_obj.create_response()
        response.async_set_speech(spoken_message)
        return response

class StopReminderIntentHandler(intent.IntentHandler):
    """Handle StopReminder intents."""

    intent_type = "StopReminder"

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        coordinator = _resolve_coordinator(hass)

        if coordinator is None:
            _LOGGER.warning("StopReminder intent received but coordinator unavailable")
            response = intent_obj.create_response()
            response.async_set_speech("I couldn't reach the reminders system right now.")
            return response

        active_id = _find_active_item_id(coordinator, is_alarm=False)

        if active_id:
            await coordinator.stop_item(active_id, False)
            spoken_message = "Reminder stopped"
        else:
            spoken_message = "There aren't any reminders playing right now."

        response = intent_obj.create_response()
        response.async_set_speech(spoken_message)
        return response

class SnoozeAlarmIntentHandler(intent.IntentHandler):
    """Handle SnoozeAlarm intents."""

    intent_type = "SnoozeAlarm"
    slot_schema = {
        vol.Optional("minutes"): vol.Coerce(int),
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        requested = slots.get("minutes", {}).get("value")
        coordinator = _resolve_coordinator(hass)

        if coordinator is None:
            _LOGGER.warning("SnoozeAlarm intent received but coordinator unavailable")
            response = intent_obj.create_response()
            response.async_set_speech("I couldn't reach the alarms system right now.")
            return response

        default_minutes = coordinator.get_default_snooze_minutes()
        minutes = int(requested) if requested else default_minutes

        active_id = _find_active_item_id(coordinator, is_alarm=True)

        if not active_id:
            response = intent_obj.create_response()
            response.async_set_speech("There isn't an alarm ringing to snooze.")
            return response

        await coordinator.snooze_item(active_id, int(minutes), True)

        response = intent_obj.create_response()
        response.async_set_speech(f"Alarm snoozed for {int(minutes)} minutes")
        return response

class SnoozeReminderIntentHandler(intent.IntentHandler):
    """Handle SnoozeReminder intents."""

    intent_type = "SnoozeReminder"
    slot_schema = {
        vol.Optional("minutes"): vol.Coerce(int),
    }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        requested = slots.get("minutes", {}).get("value")
        coordinator = _resolve_coordinator(hass)

        if coordinator is None:
            _LOGGER.warning("SnoozeReminder intent received but coordinator unavailable")
            response = intent_obj.create_response()
            response.async_set_speech("I couldn't reach the reminders system right now.")
            return response

        default_minutes = coordinator.get_default_snooze_minutes()
        minutes = int(requested) if requested else default_minutes

        active_id = _find_active_item_id(coordinator, is_alarm=False)

        if not active_id:
            response = intent_obj.create_response()
            response.async_set_speech("There isn't a reminder playing to snooze.")
            return response

        await coordinator.snooze_item(active_id, int(minutes), False)

        response = intent_obj.create_response()
        response.async_set_speech(f"Reminder snoozed for {int(minutes)} minutes")
        return response
