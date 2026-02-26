#!/usr/bin/env python3
"""
Lead Monitor - Continuous GHL Pipeline Monitoring
Detects stage changes, new calls, notes, and updates daily sales log
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Config
GHL_API_KEY = os.getenv("GHL_API_KEY", "pit-97e98eda-a14c-459e-8f09-54697e5b6aa0")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "PdIgtcGWQIP0bTKRUZup")
GHL_CALENDAR_ID = os.getenv("GHL_CALENDAR_ID", "S0ooTx8cQ86CT9eKF6Ez")
BASE_URL = "https://services.leadconnectorhq.com"
HEADERS = {
    "Authorization": f"Bearer {GHL_API_KEY}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

# PST timezone for calendar operations
PST = timezone(timedelta(hours=-8))


def datetime_to_ms(dt: datetime) -> int:
    """Convert datetime to Unix milliseconds (required by GHL calendar API)"""
    return int(dt.timestamp() * 1000)


def ms_to_datetime(ms: int, tz: timezone = None) -> datetime:
    """Convert Unix milliseconds to datetime"""
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    if tz:
        dt = dt.astimezone(tz)
    return dt


def fetch_calendar_events(date: datetime = None, calendar_id: str = None) -> List[Dict]:
    """
    Fetch calendar events for a specific day using Unix milliseconds.
    
    Args:
        date: Date to fetch events for (defaults to today in PST)
        calendar_id: GHL Calendar ID (defaults to GHL_CALENDAR_ID)
    
    Returns:
        List of calendar event dictionaries
    """
    if date is None:
        date = datetime.now(PST)
    
    if calendar_id is None:
        calendar_id = GHL_CALENDAR_ID
    
    # Calculate start and end of day in Unix milliseconds
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    start_ms = datetime_to_ms(start_of_day)
    end_ms = datetime_to_ms(end_of_day)
    
    print(f"Fetching calendar events: {start_of_day.strftime('%Y-%m-%d')} PST")
    print(f"  startTime: {start_ms} ({start_of_day.isoformat()})")
    print(f"  endTime: {end_ms} ({end_of_day.isoformat()})")
    
    # API requires Unix milliseconds for startTime and endTime
    params = {
        "calendarId": calendar_id,
        "locationId": GHL_LOCATION_ID,
        "startTime": start_ms,  # Unix milliseconds (NOT ISO string!)
        "endTime": end_ms       # Unix milliseconds (NOT ISO string!)
    }
    
    response = requests.get(
        f"{BASE_URL}/calendars/events",
        headers={
            "Authorization": f"Bearer {GHL_API_KEY}",
            "Version": "2021-07-28",
            "Accept": "application/json"
        },
        params=params
    )
    
    if response.status_code == 200:
        events = response.json().get("events", [])
        print(f"  Found {len(events)} events")
        return events
    else:
        print(f"  Error {response.status_code}: {response.text[:200]}")
        return []


def get_todays_appointments() -> List[Dict]:
    """Get today's appointments formatted for display"""
    events = fetch_calendar_events()
    appointments = []
    
    for event in events:
        # Extract appointment info
        contact_name = event.get("title") or event.get("contact", {}).get("name", "Unknown")
        
        # Parse start time (API returns ISO string in response)
        start_str = event.get("startTime") or event.get("start")
        if start_str:
            try:
                if isinstance(start_str, int):
                    start_dt = ms_to_datetime(start_str, PST)
                else:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone(PST)
                time_str = start_dt.strftime("%I:%M %p").lstrip("0")
            except:
                time_str = "TBD"
        else:
            time_str = "TBD"
        
        appointments.append({
            "name": contact_name,
            "time": time_str,
            "status": event.get("status", "confirmed"),
            "notes": event.get("notes", "")
        })
    
    # Sort by time
    appointments.sort(key=lambda x: x["time"])
    return appointments

# Pipeline: "0 - CarePlus 2" (ID: sRwU1WEbtqJtfeY4caxk)
CAREPLUS_PIPELINE_ID = "sRwU1WEbtqJtfeY4caxk"
PIPELINE_STAGES = {
    "5da091c9-53db-4ece-b171-6f8e054011c8": "Setter Reset",
    "eb3abfd5-19fc-4c35-b830-03313199b111": "New Lead",
    "d7eeda5a-59ab-4c31-a5fd-e69488383aa9": "Already Has Solar",
    "d1d0d62e-f9e9-42ba-a0c8-0734c8d0da73": "Follow Up Needed",
    "8b167e47-e4a0-4efc-9129-30ed669ac8dd": "New Lead (Pre-Booked)",
    "06ddd45b-c2eb-48c4-846d-834a7b74dea2": "Appt Set (for Closer)",
    "7237a848-975f-44c4-92ba-e9809429910e": "Presented",
    "f31f2675-a541-464a-ade5-77ad18f0f263": "Follow-Up-Appt",
    "9d5e0478-e6b8-44e4-a691-4c7a74c1c852": "Credit Approved",
    "ba97c14b-0cbe-47dd-89d1-bc3d5d0a87c4": "SPA - Sold",
    "b39bd655-ccce-4d6f-890d-5e5fd7b7267e": "Installed",
    "c0ac2459-1677-454f-9b7c-b8b944da89d9": "PTO",
    "c29613ff-cdfb-47f2-a4ab-18946ad0ad2f": "Add Ons - Waitlist",
    "59b225a9-82cd-4531-a927-c8cd8f0b7e6f": "Send to Adam",
    "a1b99c65-b587-40c8-b099-1a5e4007272b": "Send to CarePlus For All",
    "55255965-16e6-4b71-b7ca-980e70e5d019": "Credit DQ",
    "3b525630-0067-44dc-b2bf-f62aac7284be": "DQ-Other",
    "bbab373c-814e-43a9-aa18-5a68e04d2712": "Not Interested",
    "7445be6b-dcc6-4ae9-ac92-146108a66e69": "New Lead (Pre-Booked for Riley)",
}

# Stage transition outcome mapping (using "0 - CarePlus 2" stage names)
STAGE_OUTCOMES = {
    ("Appt Set (for Closer)", "SPA - Sold"): "sold",
    ("Appt Set (for Closer)", "Credit Approved"): "credit approved, pending presentation",
    ("Appt Set (for Closer)", "Presented"): "proposal delivered",
    ("Appt Set (for Closer)", "Follow-Up-Appt"): "rescheduled",
    ("Appt Set (for Closer)", "Follow Up Needed"): "rescheduled",
    ("Appt Set (for Closer)", "Credit DQ"): "credit DQ",
    ("Appt Set (for Closer)", "DQ-Other"): "not qualified",
    ("Appt Set (for Closer)", "Not Interested"): "not interested",
    ("Credit Approved", "SPA - Sold"): "sold",
    ("Presented", "SPA - Sold"): "sold",
    ("Presented", "Credit Approved"): "credit approved",
    ("Follow-Up-Appt", "SPA - Sold"): "sold",
}

# Leads to monitor (with alternate names)
MONITOR_LEADS = [
    "Cathy Johnson",
    "Chris Rivera",
    "Vy Li",
    "Mary Velez",
    "Glenn Taplin",
    "Richard Allen",
    "Nancy Castanuela",
    "Herson Sariles",
    "Donnie Cantaloupi",
    "Alfredo Gonzalez",
    "Ana Hernandes",
]

# Alternate name mappings for flexible matching
NAME_ALIASES = {
    "Nancy Castanuela": ["Nancy Or Jimmy Castanuela", "Jimmy Castanuela"],
    "Vy Li": ["tran nguyen ai vy"],
}

STATE_FILE = Path("/home/ubuntu/hot-10-dashboard/monitor_state.json")
LOG_FILE = Path("/home/ubuntu/hot-10-dashboard/daily-sales-log.md")


def get_opportunities(limit: int = 100, pipeline_id: str = None) -> List[Dict]:
    """Get opportunities from GHL, optionally filtered by pipeline"""
    response = requests.post(
        f"{BASE_URL}/opportunities/search",
        headers=HEADERS,
        json={"locationId": GHL_LOCATION_ID, "limit": limit}
    )
    if response.status_code == 201:
        opportunities = response.json().get("opportunities", [])
        # Filter by pipeline client-side (API doesn't support pipelineId filter)
        if pipeline_id:
            opportunities = [o for o in opportunities if o.get("pipelineId") == pipeline_id]
        return opportunities
    return []


def get_contact(contact_id: str) -> Dict:
    """Get contact details"""
    response = requests.get(
        f"{BASE_URL}/contacts/{contact_id}",
        headers=HEADERS
    )
    if response.status_code == 200:
        return response.json().get("contact", {})
    return {}


def get_contact_notes(contact_id: str) -> List[Dict]:
    """Get notes for a contact"""
    response = requests.get(
        f"{BASE_URL}/contacts/{contact_id}/notes",
        headers=HEADERS
    )
    if response.status_code == 200:
        return response.json().get("notes", [])
    return []


def get_recent_calls(contact_id: str, minutes_back: int = 30) -> List[Dict]:
    """Get recent calls for a contact"""
    calls = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes_back)
    
    # Search conversations
    search_resp = requests.get(
        f"{BASE_URL}/conversations/search",
        headers=HEADERS,
        params={"contactId": contact_id}
    )
    
    if search_resp.status_code != 200:
        return calls
    
    conversations = search_resp.json().get("conversations", [])
    
    for conv in conversations:
        conv_id = conv.get("id")
        if not conv_id:
            continue
        
        msg_resp = requests.get(
            f"{BASE_URL}/conversations/{conv_id}/messages",
            headers=HEADERS
        )
        
        if msg_resp.status_code != 200:
            continue
        
        messages = msg_resp.json().get("messages", {}).get("messages", [])
        
        for msg in messages:
            msg_type = msg.get("type")
            if msg_type not in [1, 31, 34, "Call", "call"]:
                continue
            
            call_date = msg.get("dateAdded")
            if call_date:
                try:
                    call_dt = datetime.fromisoformat(call_date.replace("Z", "+00:00"))
                    if call_dt > cutoff:
                        calls.append({
                            "id": msg.get("id"),
                            "date": call_date,
                            "duration": msg.get("callDuration", 0),
                            "direction": msg.get("direction"),
                        })
                except:
                    pass
    
    return calls


def load_state() -> Dict:
    """Load previous monitoring state"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"leads": {}, "last_check": None}


def save_state(state: Dict):
    """Save monitoring state"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def find_lead_opportunity(name: str, opportunities: List[Dict]) -> Optional[Dict]:
    """Find opportunity by contact name (flexible matching)"""
    # Get all names to search for
    names_to_check = [name.lower()]
    if name in NAME_ALIASES:
        names_to_check.extend([n.lower() for n in NAME_ALIASES[name]])
    
    for check_name in names_to_check:
        name_parts = check_name.split()
        
        for opp in opportunities:
            contact = opp.get("contact", {})
            contact_name = (contact.get("name") or "").lower()
            first_name = (contact.get("firstName") or "").lower()
            last_name = (contact.get("lastName") or "").lower()
            opp_name = (opp.get("name") or "").lower()
            
            # Direct name match on contact name or opportunity name
            if check_name in contact_name or contact_name == check_name:
                return opp
            if check_name in opp_name or opp_name == check_name:
                return opp
            
            # Check first/last name parts
            full_name = f"{first_name} {last_name}"
            if all(part in full_name for part in name_parts):
                return opp
            
            # Partial match on first and last
            if len(name_parts) >= 2:
                if name_parts[0] in first_name and name_parts[-1] in last_name:
                    return opp
                if name_parts[0] in opp_name and name_parts[-1] in opp_name:
                    return opp
    
    return None


def detect_changes(lead_name: str, current: Dict, previous: Optional[Dict]) -> List[Dict]:
    """Detect changes between current and previous state"""
    changes = []
    
    if not previous:
        # New lead being tracked
        changes.append({
            "type": "new_tracking",
            "message": f"Now monitoring {lead_name}",
            "stage": current.get("stage_name", "Unknown")
        })
        return changes
    
    # Check stage change
    old_stage = previous.get("stage_name", "")
    new_stage = current.get("stage_name", "")
    
    if old_stage != new_stage:
        outcome = STAGE_OUTCOMES.get((old_stage, new_stage), f"moved to {new_stage}")
        changes.append({
            "type": "stage_change",
            "from_stage": old_stage,
            "to_stage": new_stage,
            "outcome": outcome,
            "message": f"Stage: {old_stage} → {new_stage}"
        })
    
    # Check for new notes
    old_notes = previous.get("note_count", 0)
    new_notes = current.get("note_count", 0)
    
    if new_notes > old_notes:
        changes.append({
            "type": "new_notes",
            "count": new_notes - old_notes,
            "message": f"{new_notes - old_notes} new note(s)"
        })
    
    # Check for recent calls
    recent_calls = current.get("recent_calls", [])
    if recent_calls:
        for call in recent_calls:
            changes.append({
                "type": "call",
                "duration": call.get("duration", 0),
                "direction": call.get("direction", "unknown"),
                "message": f"Call ({call.get('duration', 0)}s, {call.get('direction', 'unknown')})"
            })
    
    return changes


def scan_leads() -> Tuple[Dict[str, Dict], List[Dict]]:
    """Scan all monitored leads and detect changes"""
    print(f"\n{'='*60}")
    print(f"Lead Monitor Scan - {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")
    
    # Load previous state
    state = load_state()
    previous_leads = state.get("leads", {})
    
    # Get opportunities from "0 - CarePlus 2" pipeline only
    opportunities = get_opportunities(limit=200, pipeline_id=CAREPLUS_PIPELINE_ID)
    print(f"Fetched {len(opportunities)} opportunities from '0 - CarePlus 2' pipeline\n")
    
    current_leads = {}
    all_changes = []
    
    for lead_name in MONITOR_LEADS:
        print(f"Scanning: {lead_name}...")
        
        opp = find_lead_opportunity(lead_name, opportunities)
        
        if not opp:
            print(f"  ⚠️ Not found in pipeline")
            continue
        
        contact_id = opp.get("contact", {}).get("id")
        stage_id = opp.get("pipelineStageId", "")
        stage_name = PIPELINE_STAGES.get(stage_id, "Unknown")
        
        # Get additional data
        notes = get_contact_notes(contact_id) if contact_id else []
        recent_calls = get_recent_calls(contact_id, minutes_back=30) if contact_id else []
        
        # Build current state
        current = {
            "opportunity_id": opp.get("id"),
            "contact_id": contact_id,
            "stage_id": stage_id,
            "stage_name": stage_name,
            "note_count": len(notes),
            "latest_note": notes[0].get("body", "") if notes else "",
            "recent_calls": recent_calls,
            "monetary_value": opp.get("monetaryValue", 0),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
        # Detect changes
        previous = previous_leads.get(lead_name)
        changes = detect_changes(lead_name, current, previous)
        
        if changes:
            for change in changes:
                change["lead_name"] = lead_name
                all_changes.append(change)
                print(f"  🔔 {change['message']}")
        else:
            print(f"  ✓ No changes (Stage: {stage_name})")
        
        current_leads[lead_name] = current
    
    # Save new state
    state["leads"] = current_leads
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    
    return current_leads, all_changes


def update_sales_log(leads: Dict[str, Dict], changes: List[Dict]):
    """Update the daily sales log with outcomes"""
    today = datetime.now().strftime("%A, %B %d, %Y")
    
    # Read current log
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            content = f.read()
    else:
        content = f"# Daily Sales Log - Brightstar Solar\n\n---\n\n## {today}\n\n"
    
    # Check if today's section exists
    if today not in content:
        # Add today's section after the first ---
        parts = content.split("---", 1)
        if len(parts) == 2:
            content = parts[0] + f"---\n\n## {today}\n\n" + parts[1]
    
    # Build updated entries for today
    entries = {}
    
    for lead_name, data in leads.items():
        stage = data.get("stage_name", "Unknown")
        
        # Determine outcome text
        outcome = ""
        
        if stage == "SPA - Sold":
            value = data.get("monetary_value", 0)
            if value:
                outcome = f"sold ${value:,.0f}"
            else:
                outcome = "sold"
        elif stage == "Credit Approved":
            outcome = "credit approved, pending presentation"
        elif stage == "Presented":
            outcome = "proposal delivered"
        elif stage == "Follow-Up-Appt" or stage == "Follow Up Needed":
            outcome = "rescheduled"
        elif stage == "Credit DQ":
            outcome = "credit DQ"
        elif stage == "DQ-Other":
            outcome = "not qualified"
        elif stage == "Not Interested":
            outcome = "not interested"
        elif stage == "Appt Set (for Closer)":
            latest_note = data.get("latest_note", "").lower()
            if "no show" in latest_note:
                outcome = "no show"
            elif "reschedul" in latest_note:
                outcome = "rescheduled"
            elif latest_note:
                # Use first 50 chars of note
                outcome = latest_note[:50].strip()
            else:
                outcome = "appointment pending"
        else:
            outcome = stage.lower()
        
        entries[lead_name] = outcome
    
    # Now update or add entries in the log
    lines = content.split('\n')
    updated_lines = []
    today_section = False
    
    for line in lines:
        if line.startswith("## ") and today in line:
            today_section = True
            updated_lines.append(line)
            continue
        elif line.startswith("## "):
            today_section = False
        
        if today_section and line.startswith("- **"):
            # Extract name from existing line
            try:
                existing_name = line.split("**")[1]
                if existing_name in entries:
                    # Update this line
                    updated_lines.append(f"- **{existing_name}** - {entries[existing_name]}")
                    del entries[existing_name]
                    continue
            except:
                pass
        
        updated_lines.append(line)
    
    # Add any remaining entries that weren't in the log
    if entries:
        # Find the today section and add entries
        final_lines = []
        today_section = False
        added = False
        
        for line in updated_lines:
            final_lines.append(line)
            
            if line.startswith("## ") and today in line:
                today_section = True
            elif today_section and not added and (line.strip() == "" or line.startswith("---")):
                # Add entries before empty line or section break
                for name, outcome in entries.items():
                    final_lines.insert(-1, f"- **{name}** - {outcome}")
                added = True
                today_section = False
        
        updated_lines = final_lines
    
    # Write updated log
    with open(LOG_FILE, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    print(f"\n✅ Updated {LOG_FILE}")


def generate_report(leads: Dict[str, Dict], changes: List[Dict]) -> str:
    """Generate a summary report"""
    report = []
    report.append(f"📊 **Lead Monitor Scan** - {datetime.now().strftime('%H:%M UTC')}")
    report.append("")
    
    if changes:
        report.append("🔔 **Changes Detected:**")
        for change in changes:
            if change["type"] == "stage_change":
                report.append(f"• **{change['lead_name']}** - {change['outcome']}")
            elif change["type"] == "call":
                report.append(f"• **{change['lead_name']}** - call {change['duration']}s")
            elif change["type"] == "new_notes":
                report.append(f"• **{change['lead_name']}** - {change['count']} new note(s)")
        report.append("")
    
    # Summary by stage
    stages = {}
    for name, data in leads.items():
        stage = data.get("stage_name", "Unknown")
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(name)
    
    report.append("📋 **Current Status:**")
    for stage in ["SPA - Sold", "Credit Approved", "Presented", "Appt Set (for Closer)", "Follow-Up-Appt"]:
        if stage in stages:
            names = ", ".join(stages[stage])
            report.append(f"• {stage}: {names}")
    
    # Other stages
    other = [s for s in stages.keys() if s not in ["SPA - Sold", "Credit Approved", "Presented", "Appt Set (for Closer)", "Follow-Up-Appt"]]
    for stage in other:
        names = ", ".join(stages[stage])
        report.append(f"• {stage}: {names}")
    
    return "\n".join(report)


def main():
    """Main monitoring function"""
    leads, changes = scan_leads()
    
    if not leads:
        print("\n⚠️ No leads found to monitor")
        return {"error": "No leads found"}
    
    # Update sales log
    update_sales_log(leads, changes)
    
    # Generate report
    report = generate_report(leads, changes)
    print(f"\n{report}")
    
    return {
        "leads_scanned": len(leads),
        "changes_detected": len(changes),
        "changes": changes,
        "report": report,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    result = main()
    print(f"\nScan complete: {result['leads_scanned']} leads, {result['changes_detected']} changes")
