from datetime import datetime, timezone

def add_metadata(payload: dict, rule_config: dict) -> dict:
    """Adds a timestamp to the payload."""
    timestamp_field = rule_config.get('timestamp_field', 'transformed_at')
    payload[timestamp_field] = datetime.now(timezone.utc).isoformat()
    print(f"  - Applied rule: add_metadata. Added field '{timestamp_field}'.")
    return payload
