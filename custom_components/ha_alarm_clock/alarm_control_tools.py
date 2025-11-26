"""LLM Tools for controlling active alarms and reminders (stop, snooze)."""
import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.util.json import JsonObjectType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class StopAlarmTool(llm.Tool):
    """Tool for stopping a ringing alarm."""

    name = "stop_alarm"
    description = "Stop or dismiss a currently ringing alarm. Use this when the user wants to turn off an alarm that is currently sounding."
    response_instruction = """
    Confirm to the user that the alarm has been stopped.
    Keep your response concise and friendly, in plain text without formatting.
    """

    parameters = vol.Schema({})

    def wrap_response(self, response: dict) -> dict:
        response["instruction"] = self.response_instruction
        return response

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the tool to stop ringing alarm."""
        _LOGGER.info("Stopping active alarms via LLM")

        try:
            # Get coordinator
            coordinator = None
            for entry_id, data in hass.data.get(DOMAIN, {}).items():
                if isinstance(data, dict) and "coordinator" in data:
                    coordinator = data["coordinator"]
                    break

            if not coordinator:
                return {"error": "Alarm system coordinator not found"}

            # Find active alarms
            active_alarms = [
                item_id for item_id, item in coordinator._active_items.items()
                if item.get("is_alarm") and item.get("status") == "active"
            ]

            if not active_alarms:
                return {"error": "No alarm is currently ringing"}

            # Stop all active alarms
            count = 0
            for alarm_id in active_alarms:
                await coordinator.stop_item(alarm_id, is_alarm=True)
                count += 1

            return self.wrap_response(
                {
                    "success": True,
                    "count": count,
                    "message": f"Stopped {count} ringing alarm{'s' if count != 1 else ''}",
                }
            )

        except Exception as e:
            _LOGGER.error("Error stopping alarm: %s", e, exc_info=True)
            return {"error": f"Failed to stop alarm: {str(e)}"}


class SnoozeAlarmTool(llm.Tool):
    """Tool for snoozing a ringing alarm."""

    name = "snooze_alarm"
    description = "Snooze a currently ringing alarm. The alarm will stop now and ring again after the snooze duration (default 5 minutes)."
    response_instruction = """
    Confirm to the user that the alarm has been snoozed and when it will ring again.
    Keep your response concise and friendly, in plain text without formatting.
    """

    parameters = vol.Schema(
        {
            vol.Optional(
                "minutes",
                description="How many minutes to snooze for. Default is 5 minutes if not specified.",
            ): int,
        }
    )

    def wrap_response(self, response: dict) -> dict:
        response["instruction"] = self.response_instruction
        return response

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the tool to snooze ringing alarm."""
        requested_minutes = tool_input.tool_args.get("minutes")

        _LOGGER.info("Snoozing alarm via LLM (requested=%s)", requested_minutes)

        try:
            # Get coordinator
            coordinator = None
            for entry_id, data in hass.data.get(DOMAIN, {}).items():
                if isinstance(data, dict) and "coordinator" in data:
                    coordinator = data["coordinator"]
                    break

            if not coordinator:
                return {"error": "Alarm system coordinator not found"}

            default_minutes = coordinator.get_default_snooze_minutes()
            minutes = (
                int(requested_minutes)
                if requested_minutes is not None
                else default_minutes
            )

            # Find active alarms
            active_alarms = [
                item_id for item_id, item in coordinator._active_items.items()
                if item.get("is_alarm") and item.get("status") == "active"
            ]

            if not active_alarms:
                return {"error": "No alarm is currently ringing"}

            # Snooze all active alarms
            count = 0
            for alarm_id in active_alarms:
                await coordinator.snooze_item(alarm_id, minutes, is_alarm=True)
                count += 1

            return self.wrap_response(
                {
                    "success": True,
                    "count": count,
                    "minutes": minutes,
                    "message": f"Snoozed {count} alarm{'s' if count != 1 else ''} for {minutes} minutes",
                }
            )

        except Exception as e:
            _LOGGER.error("Error snoozing alarm: %s", e, exc_info=True)
            return {"error": f"Failed to snooze alarm: {str(e)}"}


class StopReminderTool(llm.Tool):
    """Tool for stopping a ringing reminder."""

    name = "stop_reminder"
    description = "Stop or dismiss a currently ringing reminder. Use this when the user wants to turn off a reminder that is currently sounding."
    response_instruction = """
    Confirm to the user that the reminder has been stopped.
    Keep your response concise and friendly, in plain text without formatting.
    """

    parameters = vol.Schema({})

    def wrap_response(self, response: dict) -> dict:
        response["instruction"] = self.response_instruction
        return response

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the tool to stop ringing reminder."""
        _LOGGER.info("Stopping active reminders via LLM")

        try:
            # Get coordinator
            coordinator = None
            for entry_id, data in hass.data.get(DOMAIN, {}).items():
                if isinstance(data, dict) and "coordinator" in data:
                    coordinator = data["coordinator"]
                    break

            if not coordinator:
                return {"error": "Reminder system coordinator not found"}

            # Find active reminders
            active_reminders = [
                item_id for item_id, item in coordinator._active_items.items()
                if not item.get("is_alarm") and item.get("status") == "active"
            ]

            if not active_reminders:
                return {"error": "No reminder is currently ringing"}

            # Stop all active reminders
            count = 0
            for reminder_id in active_reminders:
                await coordinator.stop_item(reminder_id, is_alarm=False)
                count += 1

            return self.wrap_response(
                {
                    "success": True,
                    "count": count,
                    "message": f"Stopped {count} ringing reminder{'s' if count != 1 else ''}",
                }
            )

        except Exception as e:
            _LOGGER.error("Error stopping reminder: %s", e, exc_info=True)
            return {"error": f"Failed to stop reminder: {str(e)}"}


class SnoozeReminderTool(llm.Tool):
    """Tool for snoozing a ringing reminder."""

    name = "snooze_reminder"
    description = "Snooze a currently ringing reminder. The reminder will stop now and ring again after the snooze duration (default 5 minutes)."
    response_instruction = """
    Confirm to the user that the reminder has been snoozed and when it will ring again.
    Keep your response concise and friendly, in plain text without formatting.
    """

    parameters = vol.Schema(
        {
            vol.Optional(
                "minutes",
                description="How many minutes to snooze for. Default is 5 minutes if not specified.",
            ): int,
        }
    )

    def wrap_response(self, response: dict) -> dict:
        response["instruction"] = self.response_instruction
        return response

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        """Call the tool to snooze ringing reminder."""
        requested_minutes = tool_input.tool_args.get("minutes")

        _LOGGER.info(
            "Snoozing reminder via LLM (requested=%s)", requested_minutes
        )

        try:
            # Get coordinator
            coordinator = None
            for entry_id, data in hass.data.get(DOMAIN, {}).items():
                if isinstance(data, dict) and "coordinator" in data:
                    coordinator = data["coordinator"]
                    break

            if not coordinator:
                return {"error": "Reminder system coordinator not found"}

            default_minutes = coordinator.get_default_snooze_minutes()
            minutes = (
                int(requested_minutes)
                if requested_minutes is not None
                else default_minutes
            )

            # Find active reminders
            active_reminders = [
                item_id for item_id, item in coordinator._active_items.items()
                if not item.get("is_alarm") and item.get("status") == "active"
            ]

            if not active_reminders:
                return {"error": "No reminder is currently ringing"}

            # Snooze all active reminders
            count = 0
            for reminder_id in active_reminders:
                await coordinator.snooze_item(reminder_id, minutes, is_alarm=False)
                count += 1

            return self.wrap_response(
                {
                    "success": True,
                    "count": count,
                    "minutes": minutes,
                    "message": f"Snoozed {count} reminder{'s' if count != 1 else ''} for {minutes} minutes",
                }
            )

        except Exception as e:
            _LOGGER.error("Error snoozing reminder: %s", e, exc_info=True)
            return {"error": f"Failed to snooze reminder: {str(e)}"}
