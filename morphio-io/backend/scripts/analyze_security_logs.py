#!/usr/bin/env python3
"""
Security Log Analysis Tool

This script helps analyze security logs to identify potential security issues, suspicious
activities, and patterns. It provides summary statistics, filtering capabilities,
and alerts for potentially malicious activities.

Usage:
    python analyze_security_logs.py [options]

Options:
    --file PATH         Security log file path (default: log_files/security.log)
    --start DATE        Start date for analysis (YYYY-MM-DD)
    --end DATE          End date for analysis (YYYY-MM-DD)
    --user USER_ID      Filter by user ID
    --event TYPE        Filter by event type
    --level LEVEL       Filter by level (AUDIT, ALERT, etc.)
    --ip IP_ADDR        Filter by IP address
    --export PATH       Export results to CSV/JSON file
    --alert-only        Show only alertable events
"""

import argparse
import csv
import datetime
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Optional


def parse_log_line(line: str) -> Optional[Dict]:
    """
    Parse a log line into a structured dictionary.
    Returns None if line doesn't contain valid JSON.
    """
    try:
        # Extract the JSON part from the log line
        log_parts = line.strip().split(" [")
        if len(log_parts) < 3:
            return None

        timestamp_str = log_parts[0]
        # Find the JSON payload after the initial log metadata
        json_start = line.find("{")
        if json_start == -1:
            return None

        json_data = line[json_start:]
        log_data = json.loads(json_data)

        # Add the timestamp from the log format
        log_data["log_timestamp"] = timestamp_str

        return log_data
    except json.JSONDecodeError, ValueError, IndexError:
        return None


def filter_events(
    events: List[Dict],
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    level: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> List[Dict]:
    """Filter events based on criteria."""
    filtered = []

    for event in events:
        # Apply each filter if specified
        if start_date and "timestamp" in event:
            try:
                event_time = datetime.datetime.fromisoformat(event["timestamp"])
                if event_time < start_date:
                    continue
            except ValueError, TypeError:
                continue

        if end_date and "timestamp" in event:
            try:
                event_time = datetime.datetime.fromisoformat(event["timestamp"])
                if event_time > end_date:
                    continue
            except ValueError, TypeError:
                continue

        if user_id and event.get("user_id") != user_id:
            continue

        if event_type and event.get("event_type") != event_type:
            continue

        if ip_address and event.get("ip_address") != ip_address:
            continue

        filtered.append(event)

    return filtered


def generate_summary(events: List[Dict]) -> Dict:
    """Generate summary statistics from the events."""
    if not events:
        return {"error": "No events found matching criteria"}

    total_events = len(events)
    event_types = Counter(event.get("event_type", "UNKNOWN") for event in events)
    user_counts = Counter(str(event.get("user_id", "UNKNOWN")) for event in events)
    ip_counts = Counter(event.get("ip_address", "UNKNOWN") for event in events)

    # Find time range
    timestamps = []
    for event in events:
        if "timestamp" in event:
            try:
                timestamps.append(datetime.datetime.fromisoformat(event["timestamp"]))
            except ValueError, TypeError:
                continue

    time_range = {}
    if timestamps:
        time_range = {
            "start": min(timestamps).isoformat(),
            "end": max(timestamps).isoformat(),
            "duration_hours": (max(timestamps) - min(timestamps)).total_seconds() / 3600,
        }

    # Count failed vs successful logins
    login_success = sum(1 for e in events if e.get("event_type") == "LOGIN_SUCCESS")
    login_failure = sum(1 for e in events if e.get("event_type") == "LOGIN_FAILURE")
    access_denied = sum(1 for e in events if e.get("event_type") == "ACCESS_DENIED")

    # Get failed login reasons if available
    failure_reasons = Counter()
    for event in events:
        if event.get("event_type") == "LOGIN_FAILURE" and "details" in event:
            details = event.get("details", {})
            reason = details.get("reason", "UNKNOWN")
            failure_reasons[reason] += 1

    return {
        "total_events": total_events,
        "event_types": dict(event_types),
        "top_users": dict(user_counts.most_common(10)),
        "top_ips": dict(ip_counts.most_common(10)),
        "time_range": time_range,
        "login_stats": {
            "success": login_success,
            "failure": login_failure,
            "access_denied": access_denied,
            "failure_ratio": (
                login_failure / (login_success + login_failure)
                if (login_success + login_failure) > 0
                else 0
            ),
            "failure_reasons": dict(failure_reasons),
        },
    }


def find_suspicious_events(events: List[Dict]) -> List[Dict]:
    """
    Identify potentially suspicious events based on heuristics.
    """
    suspicious = []

    # Track failed login attempts per user and IP
    failed_logins_by_user = defaultdict(int)
    failed_logins_by_ip = defaultdict(int)

    # Track event times by user for unusual timing patterns
    user_event_times = defaultdict(list)

    # Analyze each event
    for event in events:
        event_type = event.get("event_type", "")
        user_id = event.get("user_id")
        ip_address = event.get("ip_address")

        # Check for explicitly suspicious event types
        if event_type in [
            "SUSPICIOUS_ACTIVITY",
            "RATE_LIMIT_EXCEEDED",
            "ACCOUNT_LOCKED",
            "TOKEN_VERIFICATION_FAILED",
            "TOKEN_CREATION_FAILED",
        ]:
            suspicious.append(
                {
                    "event": event,
                    "reason": f"Explicit {event_type} event",
                    "severity": "HIGH",
                }
            )

        # Track failed logins
        if event_type == "LOGIN_FAILURE":
            if user_id:
                failed_logins_by_user[user_id] += 1
            if ip_address:
                failed_logins_by_ip[ip_address] += 1

        # Track user event timing
        if user_id and "timestamp" in event:
            try:
                timestamp = datetime.datetime.fromisoformat(event["timestamp"])
                user_event_times[user_id].append(timestamp)
            except ValueError, TypeError:
                pass

    # Analyze for suspicious patterns

    # Multiple failed logins from same user
    for user_id, count in failed_logins_by_user.items():
        if count >= 3:
            relevant_events = [
                e
                for e in events
                if e.get("user_id") == user_id and e.get("event_type") == "LOGIN_FAILURE"
            ]
            suspicious.append(
                {
                    "events": relevant_events,
                    "reason": f"Multiple failed logins ({count}) for user {user_id}",
                    "severity": "MEDIUM" if count < 5 else "HIGH",
                }
            )

    # Multiple failed logins from same IP
    for ip, count in failed_logins_by_ip.items():
        if count >= 5:
            relevant_events = [
                e
                for e in events
                if e.get("ip_address") == ip and e.get("event_type") == "LOGIN_FAILURE"
            ]
            suspicious.append(
                {
                    "events": relevant_events,
                    "reason": f"Multiple failed logins ({count}) from IP {ip}",
                    "severity": "MEDIUM" if count < 10 else "HIGH",
                }
            )

    # Unusual login timing/frequency
    for user_id, timestamps in user_event_times.items():
        if len(timestamps) < 2:
            continue

        # Sort timestamps
        timestamps.sort()

        # Check for very frequent login/activity
        for i in range(len(timestamps) - 1):
            time_diff = (timestamps[i + 1] - timestamps[i]).total_seconds()
            if time_diff < 1.0:  # Less than 1 second between events
                suspicious.append(
                    {
                        "user_id": user_id,
                        "reason": f"Unusually fast activity for user {user_id} ({time_diff:.2f} seconds between events)",
                        "severity": "MEDIUM",
                        "timestamp1": timestamps[i].isoformat(),
                        "timestamp2": timestamps[i + 1].isoformat(),
                    }
                )
                break

    return suspicious


def export_results(events: List[Dict], summary: Dict, suspicious: List[Dict], export_path: str):
    """Export analysis results to a file."""
    results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event_count": len(events),
        "summary": summary,
        "suspicious_activity": suspicious,
    }

    file_ext = os.path.splitext(export_path)[1].lower()

    if file_ext == ".json":
        with open(export_path, "w") as f:
            json.dump(results, f, indent=2)
    elif file_ext == ".csv":
        # For CSV, we'll just export the events in a flattened structure
        with open(export_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Write header
            if events:
                # Get all possible fields from all events
                fields = set()
                for event in events:
                    fields.update(event.keys())
                writer.writerow(sorted(fields))

                # Write events
                for event in events:
                    row = [event.get(field, "") for field in sorted(fields)]
                    writer.writerow(row)
    else:
        # Default to JSON
        with open(export_path, "w") as f:
            json.dump(results, f, indent=2)

    print(f"Results exported to {export_path}")


def main():
    parser = argparse.ArgumentParser(description="Security Log Analysis Tool")
    parser.add_argument("--file", default="log_files/security.log", help="Security log file path")
    parser.add_argument("--start", help="Start date for analysis (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date for analysis (YYYY-MM-DD)")
    parser.add_argument("--user", help="Filter by user ID")
    parser.add_argument("--event", help="Filter by event type")
    parser.add_argument("--level", help="Filter by level (AUDIT, ALERT, etc.)")
    parser.add_argument("--ip", help="Filter by IP address")
    parser.add_argument("--export", help="Export results to CSV/JSON file")
    parser.add_argument("--alert-only", action="store_true", help="Show only alertable events")

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.file):
        print(f"Error: Log file not found: {args.file}")
        return 1

    start_date = None
    if args.start:
        try:
            start_date = datetime.datetime.fromisoformat(args.start)
        except ValueError:
            print(f"Error: Invalid start date format: {args.start}. Use YYYY-MM-DD.")
            return 1

    end_date = None
    if args.end:
        try:
            end_date = datetime.datetime.fromisoformat(args.end)
        except ValueError:
            print(f"Error: Invalid end date format: {args.end}. Use YYYY-MM-DD.")
            return 1

    # Read and parse log file
    events = []
    print(f"Reading log file: {args.file}")

    with open(args.file, "r") as f:
        for line in f:
            event = parse_log_line(line)
            if event:
                events.append(event)

    print(f"Found {len(events)} events in log file")

    # Apply filters
    filtered_events = filter_events(
        events,
        start_date=start_date,
        end_date=end_date,
        user_id=args.user,
        event_type=args.event,
        level=args.level,
        ip_address=args.ip,
    )

    print(f"After filtering: {len(filtered_events)} events")

    if not filtered_events:
        print("No events match the specified criteria.")
        return 0

    # Generate summary
    summary = generate_summary(filtered_events)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))

    # Find suspicious events
    suspicious = find_suspicious_events(filtered_events)

    if suspicious:
        print(f"\n=== SUSPICIOUS ACTIVITY ({len(suspicious)} incidents) ===")
        for i, incident in enumerate(suspicious, 1):
            print(f"\n{i}. {incident['reason']} (Severity: {incident.get('severity', 'UNKNOWN')})")
    else:
        print("\nNo suspicious activity detected.")

    # Export if requested
    if args.export:
        export_results(filtered_events, summary, suspicious, args.export)

    return 0


if __name__ == "__main__":
    sys.exit(main())
