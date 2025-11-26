DEFAULT_SENTENCES = {
    "language": "en",
    "intents": {
        "SetReminder": {
            "data": [
                {
                    "sentences": [
                        "remind me to {task} at {datetime}",
                        "set a reminder for {task} at {datetime}",
                        "remind me about {task} on {datetime}",
                        "create a reminder for {task} at {datetime}",
                        "set reminder to {task} for {datetime}"
                    ]
                }
            ]
        },
        "StopReminder": {
            "data": [
                {
                    "sentences": [
                        "stop [the] reminder",
                        "turn off [the] reminder",
                        "disable [the] reminder",
                        "cancel [the] reminder",
                        "dismiss [the] reminder"
                    ]
                }
            ]
        },
        "SnoozeReminder": {
            "data": [
                {
                    "sentences": [
                        "snooze [the] reminder",
                        "snooze reminder [for] {minutes} minutes",
                        "remind me again in {minutes} minutes",
                        "postpone [the] reminder [for] {minutes} minutes"
                    ]
                }
            ]
        }
    },
    "lists": {
        "task": {
            "type": "text",
            "wildcard": True,
        },
        "datetime": {
            "type": "text",
            "values": [
                "in {time}",
                "at {time}",
                "{time} on {date}",
                "today at {time}",
                "tomorrow at {time}",
                "the day after tomorrow at {time}",
                "on {date} at {time}"
            ]
        },
        "time": {
            "type": "text",
            "values": [
                "{hour}:{minute} AM",
                "{hour}:{minute} PM",
                "{hour} {minute} AM",
                "{hour} {minute} PM",
                "{hour} AM",
                "{hour} PM"
            ]
        },
        "hour": {
            "type": "number",
            "range": [
                {"from": 1, "to": 12}
            ]
        },
        "minute": {
            "type": "number",
            "range": [
                {"from": 0, "to": 59, "step": 1}
            ]
        },
        "date": {
            "type": "text",
            "values": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
                "next Monday",
                "next Tuesday",
                "next Wednesday",
                "next Thursday",
                "next Friday",
                "next Saturday",
                "next Sunday"
            ]
        },
        "minutes": {
            "type": "number",
            "range": [
                {"from": 1, "to": 60}
            ]
        }
    }
}
