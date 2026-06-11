# app/core/state.py
# Simple memory store (restart hone par reset ho jayega)
pending_commands = {} # {device_id: "app" or "schedule" or "timer"}