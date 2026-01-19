#!/usr/bin/env python3
"""
ActivityWatch Server with MySQL Backend
Enterprise Edition - Full aw-webui Compatible
"""

import os
import sys
import socket
import logging
from flask import Flask, request, jsonify, g, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import text, func
from datetime import datetime, timezone, timedelta

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = "mysql+pymysql://awuser:awpassword@localhost:3306/activitywatch_local"
SECRET_KEY = "your-secret-key-change-in-production"
HOSTNAME = socket.gethostname()

# Skip JWT auth for testing
ENABLE_AUTH = False

# Initialize Flask App
# Static folder points to aw-webui/dist (relative to parent directory)
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEBUI_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'aw-webui', 'dist')
app = Flask(__name__, static_folder=WEBUI_DIR)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

# Enable CORS for browser requests
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize Database
db = SQLAlchemy(app)

# Log all requests to file
import atexit
_request_log_file = open('c:/Users/user458/activitywatch/request_log.txt', 'a')
atexit.register(lambda: _request_log_file.close())

@app.before_request
def log_request():
    if request.path.startswith('/api/'):
        _request_log_file.write(f"REQUEST: {request.method} {request.path}\n")
        _request_log_file.flush()

@app.after_request
def log_response(response):
    if request.path.startswith('/api/'):
        _request_log_file.write(f"RESPONSE: {request.path} -> {response.status_code}\n")
        _request_log_file.flush()
    return response

# ============================================
# DATABASE MODELS
# ============================================

class Bucket(db.Model):
    """Bucket model - containers for events"""
    __tablename__ = 'buckets'

    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255))
    type = db.Column(db.String(50))
    client = db.Column(db.String(100))
    hostname = db.Column(db.String(255))
    created = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSON, default=dict)
    # Enterprise fields
    employee_id = db.Column(db.String(50), default='default')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'client': self.client,
            'hostname': self.hostname,
            'created': self.created.isoformat() + 'Z' if self.created else None,
            'data': self.data or {}
        }


class Event(db.Model):
    """Event model - activity events"""
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bucket_id = db.Column(db.String(255), db.ForeignKey('buckets.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Float, default=0.0)
    data = db.Column(db.JSON)
    # Enterprise fields
    employee_id = db.Column(db.String(50), default='default')
    device_id = db.Column(db.String(100))
    office_location = db.Column(db.String(50))
    privacy_level = db.Column(db.String(20), default='normal')

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() + 'Z' if self.timestamp else None,
            'duration': self.duration or 0,
            'data': self.data or {}
        }


class Employee(db.Model):
    """Employee model for multi-user support"""
    __tablename__ = 'employees'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    department = db.Column(db.String(50))
    role = db.Column(db.String(20), default='employee')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship to devices
    devices = db.relationship('Device', backref='employee', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None
        }


class Device(db.Model):
    """Device model - tracks employee devices"""
    __tablename__ = 'devices'

    id = db.Column(db.String(100), primary_key=True)  # hostname or unique device ID
    employee_id = db.Column(db.String(50), db.ForeignKey('employees.id'), nullable=False)
    hostname = db.Column(db.String(255))
    device_type = db.Column(db.String(50), default='desktop')  # desktop, laptop, mobile
    os_info = db.Column(db.String(100))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'hostname': self.hostname,
            'device_type': self.device_type,
            'os_info': self.os_info,
            'last_seen': self.last_seen.isoformat() + 'Z' if self.last_seen else None,
            'is_active': self.is_active
        }


# Create tables on startup
with app.app_context():
    db.create_all()
    print("[OK] Database tables created")

# ============================================
# CORE API ENDPOINTS (Required by aw-webui)
# ============================================

@app.route("/api/0/info", methods=["GET"])
def info():
    """Server info - required by aw-webui"""
    return jsonify({
        "hostname": HOSTNAME,
        "version": "0.13.0",
        "testing": False,
        "device_id": HOSTNAME
    })


@app.route("/api/0/settings", methods=["GET"])
def get_settings():
    """Get settings - required by aw-webui"""
    return jsonify({})


@app.route("/api/0/settings", methods=["POST"])
def update_settings():
    """Update settings"""
    return jsonify({})


@app.route("/api/0/", methods=["GET"])
def api_root():
    """API root"""
    return jsonify({
        "message": "ActivityWatch API",
        "version": "0.13.0"
    })


# ============================================
# BUCKET ENDPOINTS
# ============================================

@app.route("/api/0/buckets/", methods=["GET"])
def get_buckets():
    """List all buckets"""
    employee_id = request.args.get('employee_id', 'default')

    # If admin, can filter by employee
    if employee_id and employee_id != 'default':
        buckets = Bucket.query.filter_by(employee_id=employee_id).all()
    else:
        buckets = Bucket.query.all()

    return jsonify({b.id: b.to_dict() for b in buckets})


@app.route("/api/0/buckets/<bucket_id>", methods=["GET"])
def get_bucket(bucket_id):
    """Get a specific bucket"""
    bucket = Bucket.query.get(bucket_id)
    if not bucket:
        return jsonify({"error": "Bucket not found"}), 404
    return jsonify(bucket.to_dict())


@app.route("/api/0/buckets/<bucket_id>", methods=["POST"])
def create_bucket(bucket_id):
    """Create or update a bucket"""
    data = request.json or {}

    # Check if bucket exists
    existing = Bucket.query.get(bucket_id)
    if existing:
        # Update existing bucket with new values if provided
        if data.get('type') and data.get('type') != 'unknown':
            existing.type = data.get('type')
        if data.get('client') and data.get('client') != 'unknown':
            existing.client = data.get('client')
        if data.get('hostname'):
            existing.hostname = data.get('hostname')
        if data.get('data'):
            existing.data = data.get('data')
        db.session.commit()
        return jsonify(existing.to_dict())

    bucket = Bucket(
        id=bucket_id,
        name=data.get('name', bucket_id),
        type=data.get('type', 'unknown'),
        client=data.get('client', 'unknown'),
        hostname=data.get('hostname', HOSTNAME),
        data=data.get('data', {}),
        employee_id=data.get('employee_id', 'default')
    )
    db.session.add(bucket)
    db.session.commit()

    return jsonify(bucket.to_dict()), 200


@app.route("/api/0/buckets/<bucket_id>", methods=["DELETE"])
def delete_bucket(bucket_id):
    """Delete a bucket and its events"""
    bucket = Bucket.query.get(bucket_id)
    if not bucket:
        return jsonify({"error": "Bucket not found"}), 404

    # Delete associated events
    Event.query.filter_by(bucket_id=bucket_id).delete()
    db.session.delete(bucket)
    db.session.commit()

    return jsonify({"success": True})


# ============================================
# EVENT ENDPOINTS
# ============================================

@app.route("/api/0/buckets/<bucket_id>/events", methods=["GET"])
def get_events(bucket_id):
    """Get events from a bucket"""
    limit = request.args.get('limit', 100, type=int)
    start = request.args.get('start')
    end = request.args.get('end')

    query = Event.query.filter_by(bucket_id=bucket_id)

    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            query = query.filter(Event.timestamp >= start_dt)
        except:
            pass

    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            query = query.filter(Event.timestamp <= end_dt)
        except:
            pass

    events = query.order_by(Event.timestamp.desc()).limit(limit).all()
    return jsonify([e.to_dict() for e in events])


@app.route("/api/0/buckets/<bucket_id>/events", methods=["POST"])
def create_events(bucket_id):
    """Create events in a bucket"""
    # Ensure bucket exists
    bucket = Bucket.query.get(bucket_id)
    if not bucket:
        # Auto-create bucket
        bucket = Bucket(
            id=bucket_id,
            name=bucket_id,
            type='auto',
            client='auto',
            hostname=HOSTNAME
        )
        db.session.add(bucket)
        db.session.commit()

    data = request.json

    # Handle single event or list of events
    if isinstance(data, list):
        events_data = data
    else:
        events_data = [data]

    created_events = []
    for event_data in events_data:
        timestamp = event_data.get('timestamp')
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        # Remove timezone info for MySQL
        if timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=None)

        event = Event(
            bucket_id=bucket_id,
            timestamp=timestamp,
            duration=event_data.get('duration', 0),
            data=event_data.get('data', {}),
            employee_id=event_data.get('employee_id', 'default'),
            device_id=event_data.get('device_id')
        )
        db.session.add(event)
        created_events.append(event)

    db.session.commit()

    if len(created_events) == 1:
        return jsonify(created_events[0].to_dict()), 201
    return jsonify([e.to_dict() for e in created_events]), 201


@app.route("/api/0/buckets/<bucket_id>/events/count", methods=["GET"])
def get_event_count(bucket_id):
    """Get event count for a bucket"""
    count = Event.query.filter_by(bucket_id=bucket_id).count()
    return jsonify({"count": count})


@app.route("/api/0/buckets/<bucket_id>/heartbeat", methods=["POST"])
def heartbeat(bucket_id):
    """
    Heartbeat endpoint - merges events with pulsetime.

    This implements ActivityWatch's heartbeat mechanism:
    - Heartbeats are sent with duration=0
    - If data matches last event AND timestamp is within pulsetime of last event's end,
      the last event's duration is extended to cover the new timestamp
    - Otherwise, a new event is created

    Duration calculation: new_timestamp - last_event.timestamp
    (This gives the total time from when the state started to the latest heartbeat)
    """
    pulsetime = request.args.get('pulsetime', 60, type=float)
    data = request.json

    # Ensure bucket exists
    bucket = Bucket.query.get(bucket_id)
    if not bucket:
        bucket = Bucket(
            id=bucket_id,
            name=bucket_id,
            type='heartbeat',
            client='heartbeat',
            hostname=HOSTNAME
        )
        db.session.add(bucket)
        db.session.commit()

    # Parse timestamp
    timestamp = data.get('timestamp')
    if timestamp:
        try:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if timestamp.tzinfo:
                    timestamp = timestamp.replace(tzinfo=None)
        except:
            timestamp = datetime.utcnow()
    else:
        timestamp = datetime.utcnow()

    # Find last event in bucket
    last_event = Event.query.filter_by(bucket_id=bucket_id).order_by(
        Event.timestamp.desc()
    ).first()

    event_data = data.get('data', {})

    # Check if we should merge with last event
    # Merge if: data matches AND timestamp is within pulsetime of last event's END time
    # For heartbeats with duration=0, also check from the timestamp itself
    if last_event and last_event.data == event_data:
        # Calculate the end time of the last event
        last_event_end = last_event.timestamp + timedelta(seconds=last_event.duration)

        # Check if new heartbeat is within pulsetime of last event's end
        time_since_last_end = (timestamp - last_event_end).total_seconds()

        # Also check time since last event's start (for duration=0 heartbeats)
        time_since_last_start = (timestamp - last_event.timestamp).total_seconds()

        # Merge if within pulsetime of end, OR if duration was 0 and within pulsetime of start
        should_merge = (time_since_last_end <= pulsetime and time_since_last_end >= 0) or \
                       (last_event.duration == 0 and time_since_last_start <= pulsetime and time_since_last_start >= 0)

        if should_merge:
            # Merge - extend duration from original start to new timestamp
            # Duration = new_timestamp - original_timestamp
            new_duration = (timestamp - last_event.timestamp).total_seconds()
            last_event.duration = new_duration
            db.session.commit()
            return jsonify(last_event.to_dict())

    # Create new event (data changed or outside pulsetime window)
    # First check if an event with this exact timestamp already exists (prevent race condition duplicates)
    existing = Event.query.filter_by(bucket_id=bucket_id, timestamp=timestamp).first()
    if existing:
        # Update existing event's data if different, otherwise just return it
        if existing.data != event_data:
            existing.data = event_data
            db.session.commit()
        return jsonify(existing.to_dict())

    event = Event(
        bucket_id=bucket_id,
        timestamp=timestamp,
        duration=0,  # New events start with duration=0
        data=event_data,
        employee_id=data.get('employee_id', 'default'),
        device_id=data.get('device_id')
    )

    try:
        db.session.add(event)
        db.session.commit()
    except Exception as e:
        # Handle race condition - another request may have inserted same timestamp
        db.session.rollback()
        existing = Event.query.filter_by(bucket_id=bucket_id, timestamp=timestamp).first()
        if existing:
            return jsonify(existing.to_dict())
        raise e

    return jsonify(event.to_dict())


# ============================================
# QUERY ENDPOINT (for aw-webui queries)
# ============================================

import re

def parse_timeperiod(period):
    """Parse ISO 8601 time period string"""
    if '/' in period:
        start_str, end_str = period.split('/')
    else:
        start_str = period
        end_str = None

    try:
        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        if start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=None)
    except:
        start_dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)

    if end_str:
        try:
            end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            if end_dt.tzinfo:
                end_dt = end_dt.replace(tzinfo=None)
        except:
            end_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        end_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    return start_dt, end_dt

def parse_return_dict(expr, variables):
    """Parse complex nested RETURN dict and resolve variable references"""
    # Remove newlines and extra whitespace
    expr = re.sub(r'\s+', ' ', expr).strip()

    def resolve_value(val_str):
        """Resolve a value which could be a variable name or nested structure"""
        val_str = val_str.strip()
        if val_str.startswith('{'):
            return parse_nested_dict(val_str)
        elif val_str.startswith('['):
            return []  # Empty array literal
        else:
            # Variable reference
            return variables.get(val_str, [])

    def parse_nested_dict(dict_str):
        """Parse a nested dict structure"""
        result = {}
        # Remove outer braces
        inner = dict_str.strip()[1:-1].strip()
        if not inner:
            return result

        # Find key-value pairs (handle nested structures)
        depth = 0
        current_key = None
        current_value = ""
        in_key = True
        in_string = False
        string_char = None

        i = 0
        while i < len(inner):
            c = inner[i]

            # Track string literals
            if c in '"\'':
                if not in_string:
                    in_string = True
                    string_char = c
                elif c == string_char:
                    in_string = False
                    string_char = None

            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                elif c == ':' and depth == 0 and in_key:
                    # Extract key (remove quotes)
                    current_key = current_value.strip().strip('"\'')
                    current_value = ""
                    in_key = False
                    i += 1
                    continue
                elif c == ',' and depth == 0:
                    # End of value
                    if current_key:
                        result[current_key] = resolve_value(current_value)
                    current_key = None
                    current_value = ""
                    in_key = True
                    i += 1
                    continue

            current_value += c
            i += 1

        # Don't forget the last key-value pair
        if current_key:
            result[current_key] = resolve_value(current_value)

        return result

    return parse_nested_dict(expr)

def execute_query(query_lines, start_dt, end_dt):
    """Execute aw-query and return results"""
    variables = {}
    return_value = []

    # Get all buckets for find_bucket
    all_buckets = {b.id: b for b in Bucket.query.all()}

    for line in query_lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        # Handle RETURN statement
        if line.startswith('RETURN'):
            # Extract everything after "RETURN ="
            return_expr = re.sub(r'^RETURN\s*=\s*', '', line).rstrip(';').strip()

            # Try simple variable name first: RETURN = events
            if re.match(r'^\w+$', return_expr):
                return_value = variables.get(return_expr, [])
                continue

            # Try function call: RETURN = func(var)
            match = re.match(r'^(\w+)\((\w+)\)', return_expr)
            if match:
                func_name = match.group(1)
                var_name = match.group(2)
                events = variables.get(var_name, [])
                if func_name == 'sort_by_duration':
                    return_value = sorted(events, key=lambda e: e.get('duration', 0), reverse=True)
                elif func_name == 'sort_by_timestamp':
                    return_value = sorted(events, key=lambda e: e.get('timestamp', ''))
                elif func_name == 'sum_durations':
                    return_value = sum(e.get('duration', 0) for e in events)
                else:
                    return_value = events
                continue

            # Try complex dict/nested structure (multiline with \n)
            if return_expr.startswith('{'):
                return_value = parse_return_dict(return_expr, variables)
                continue

            continue

        # Handle variable assignment
        if '=' in line:
            var_name, expr = line.split('=', 1)
            var_name = var_name.strip()
            expr = expr.strip().rstrip(';')

            # Parse function calls
            # query_bucket(bucket_id)
            match = re.match(r'query_bucket\(["\']([^"\']+)["\']\)', expr)
            if match:
                bucket_id = match.group(1)
                events = Event.query.filter_by(bucket_id=bucket_id)\
                    .filter(Event.timestamp >= start_dt)\
                    .filter(Event.timestamp <= end_dt)\
                    .order_by(Event.timestamp).all()
                variables[var_name] = [e.to_dict() for e in events]
                continue

            # find_bucket(pattern)
            match = re.match(r'find_bucket\(["\']([^"\']+)["\']\)', expr)
            if match:
                pattern = match.group(1)
                for bid in all_buckets.keys():
                    if pattern in bid:
                        variables[var_name] = bid
                        break
                else:
                    variables[var_name] = None
                continue

            # query_bucket(find_bucket(pattern))
            match = re.match(r'query_bucket\(find_bucket\(["\']([^"\']+)["\']\)\)', expr)
            if match:
                pattern = match.group(1)
                bucket_id = None
                for bid in all_buckets.keys():
                    if pattern in bid:
                        bucket_id = bid
                        break
                if bucket_id:
                    events = Event.query.filter_by(bucket_id=bucket_id)\
                        .filter(Event.timestamp >= start_dt)\
                        .filter(Event.timestamp <= end_dt)\
                        .order_by(Event.timestamp).all()
                    variables[var_name] = [e.to_dict() for e in events]
                else:
                    variables[var_name] = []
                continue

            # merge_events_by_keys(events, keys) - merge events by keys
            # Matching original aw-core merge_events_by_keys algorithm
            match = re.match(r'merge_events_by_keys\((\w+),\s*\[([^\]]*)\]\)', expr)
            if match:
                events_var = match.group(1)
                keys_str = match.group(2)
                keys = [k.strip().strip('"\'') for k in keys_str.split(',') if k.strip()]
                events = variables.get(events_var, [])

                # Merge events by combining durations for matching keys (aw-core algorithm)
                merged = {}
                for e in events:
                    data = e.get('data', {})

                    # Build composite key only from keys that exist in event data
                    # This matches original: composite_key = composite_key + (val,) only if key in event.data
                    composite_key = ()
                    for k in keys:
                        if k in data:
                            val = data[k]
                            # Convert lists to tuples for hashability (e.g., $category)
                            if isinstance(val, list):
                                val = tuple(val)
                            composite_key = composite_key + (val,)

                    if composite_key not in merged:
                        # Create new merged event with empty data dict
                        merged[composite_key] = {
                            'timestamp': e.get('timestamp'),
                            'duration': e.get('duration', 0),
                            'data': {}
                        }
                    else:
                        # Add duration to existing merged event
                        merged[composite_key]['duration'] += e.get('duration', 0)

                    # Copy only the specified keys to merged event's data
                    for k in keys:
                        if k in data:
                            merged[composite_key]['data'][k] = data[k]

                variables[var_name] = list(merged.values())
                continue

            # flood(events) - fill gaps (also handles nested function calls)
            match = re.match(r'flood\((.+)\)\s*$', expr)
            if match:
                inner = match.group(1).strip()
                # Check if inner is a variable name or a function call
                if inner in variables:
                    variables[var_name] = variables.get(inner, [])
                else:
                    # It's a nested function call - evaluate it
                    # Handle query_bucket(find_bucket(...)) pattern
                    bucket_match = re.match(r'query_bucket\(find_bucket\(["\']([^"\']+)["\']\)\)', inner)
                    if bucket_match:
                        pattern = bucket_match.group(1)
                        bucket_id = None
                        for bid in all_buckets.keys():
                            if pattern in bid:
                                bucket_id = bid
                                break
                        if bucket_id:
                            events = Event.query.filter_by(bucket_id=bucket_id)\
                                .filter(Event.timestamp >= start_dt)\
                                .filter(Event.timestamp <= end_dt)\
                                .order_by(Event.timestamp).all()
                            variables[var_name] = [e.to_dict() for e in events]
                        else:
                            variables[var_name] = []
                    else:
                        variables[var_name] = []
                continue

            # filter_keyvals(events, key, values)
            match = re.match(r'filter_keyvals\((\w+),\s*["\'](\w+)["\'],\s*\[([^\]]*)\]\)', expr)
            if match:
                events_var = match.group(1)
                key = match.group(2)
                values_str = match.group(3)
                # Parse values - handle strings, booleans, numbers
                values = []
                for v in values_str.split(','):
                    v = v.strip()
                    if v in ('true', 'True'):
                        values.append(True)
                    elif v in ('false', 'False'):
                        values.append(False)
                    elif v.isdigit():
                        values.append(int(v))
                    else:
                        values.append(v.strip('"\''))
                events = variables.get(events_var, [])
                filtered = [e for e in events if e.get('data', {}).get(key) in values]
                variables[var_name] = filtered
                continue

            # filter_keyvals_regex - simplified
            match = re.match(r'filter_keyvals_regex\((\w+),', expr)
            if match:
                events_var = match.group(1)
                variables[var_name] = variables.get(events_var, [])
                continue

            # filter_period_intersect(events, filter_events) - filter events by time periods
            # Using the original ActivityWatch two-pointer algorithm from aw-core
            match = re.match(r'filter_period_intersect\((\w+),\s*(\w+)\)', expr)
            if match:
                events_var = match.group(1)
                filter_var = match.group(2)
                events = variables.get(events_var, [])
                filter_events = variables.get(filter_var, [])

                # If no filter events, return all events (ActivityWatch default behavior)
                if not filter_events:
                    variables[var_name] = events
                    continue

                def _parse_event_period(event):
                    """Parse event timestamp and duration, return (start, end) tuple"""
                    ts_str = event.get('timestamp', '')
                    dur = event.get('duration', 0)
                    if not ts_str:
                        return None
                    try:
                        if isinstance(ts_str, str):
                            start = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                            if start.tzinfo:
                                start = start.replace(tzinfo=None)
                        else:
                            start = ts_str
                        end = start + timedelta(seconds=dur)
                        return (start, end)
                    except:
                        return None

                # Parse and sort both event lists by timestamp (matching original algorithm)
                events1_parsed = []
                for e in events:
                    period = _parse_event_period(e)
                    if period:
                        events1_parsed.append((e, period[0], period[1]))
                events1_parsed.sort(key=lambda x: x[1])  # Sort by start time

                events2_parsed = []
                for e in filter_events:
                    period = _parse_event_period(e)
                    if period:
                        events2_parsed.append((e, period[0], period[1]))
                events2_parsed.sort(key=lambda x: x[1])  # Sort by start time

                # Two-pointer algorithm from original aw-core filter_period_intersect
                intersected_events = []
                e1_i = 0
                e2_i = 0

                while e1_i < len(events1_parsed) and e2_i < len(events2_parsed):
                    e1, e1_start, e1_end = events1_parsed[e1_i]
                    e2, e2_start, e2_end = events2_parsed[e2_i]

                    # Calculate intersection
                    intersect_start = max(e1_start, e2_start)
                    intersect_end = min(e1_end, e2_end)

                    if intersect_start < intersect_end:
                        # Events intersect - create new event with intersection period
                        intersected_event = dict(e1)
                        intersected_event['timestamp'] = intersect_start.isoformat()
                        intersected_event['duration'] = (intersect_end - intersect_start).total_seconds()
                        intersected_events.append(intersected_event)

                        # Advance the pointer for whichever event ends first
                        if e1_end <= e2_end:
                            e1_i += 1
                        else:
                            e2_i += 1
                    else:
                        # No intersection - advance the pointer for whichever event ends first
                        if e1_end <= e2_start:
                            e1_i += 1
                        elif e2_end <= e1_start:
                            e2_i += 1
                        else:
                            # Should be unreachable, but advance both to avoid infinite loop
                            e1_i += 1
                            e2_i += 1

                variables[var_name] = intersected_events
                continue

            # nop(events) - no operation, just pass through
            match = re.match(r'nop\((\w+)\)', expr)
            if match:
                events_var = match.group(1)
                variables[var_name] = variables.get(events_var, [])
                continue

            # sum_durations(events) - returns total duration
            match = re.match(r'sum_durations\((\w+)\)', expr)
            if match:
                events_var = match.group(1)
                events = variables.get(events_var, [])
                total = sum(e.get('duration', 0) for e in events)
                variables[var_name] = total
                continue

            # period_length(events, key) - simplified
            match = re.match(r'period_length\(', expr)
            if match:
                variables[var_name] = 0
                continue

            # sort_by_duration or sort_by_timestamp
            # First check for nested function call: sort_by_duration(merge_events_by_keys(...))
            match = re.match(r'sort_by_(\w+)\(merge_events_by_keys\((\w+),\s*\[([^\]]*)\]\)\)', expr)
            if match:
                sort_key = match.group(1)
                events_var = match.group(2)
                keys_str = match.group(3)
                keys = [k.strip().strip('"\'') for k in keys_str.split(',') if k.strip()]
                events = variables.get(events_var, [])

                # First merge events by keys (using aw-core algorithm)
                merged = {}
                for e in events:
                    data = e.get('data', {})

                    # Build composite key only from keys that exist in event data
                    composite_key = ()
                    for k in keys:
                        if k in data:
                            val = data[k]
                            if isinstance(val, list):
                                val = tuple(val)
                            composite_key = composite_key + (val,)

                    if composite_key not in merged:
                        merged[composite_key] = {
                            'timestamp': e.get('timestamp'),
                            'duration': e.get('duration', 0),
                            'data': {}
                        }
                    else:
                        merged[composite_key]['duration'] += e.get('duration', 0)

                    # Copy only the specified keys to merged event's data
                    for k in keys:
                        if k in data:
                            merged[composite_key]['data'][k] = data[k]

                merged_list = list(merged.values())

                # Then sort
                if sort_key == 'duration':
                    merged_list = sorted(merged_list, key=lambda e: e.get('duration', 0), reverse=True)
                elif sort_key == 'timestamp':
                    merged_list = sorted(merged_list, key=lambda e: e.get('timestamp', ''))

                variables[var_name] = merged_list
                continue

            # Simple sort: sort_by_duration(var)
            match = re.match(r'sort_by_(\w+)\((\w+)\)', expr)
            if match:
                sort_key = match.group(1)
                events_var = match.group(2)
                events = variables.get(events_var, [])
                if sort_key == 'duration':
                    events = sorted(events, key=lambda e: e.get('duration', 0), reverse=True)
                elif sort_key == 'timestamp':
                    events = sorted(events, key=lambda e: e.get('timestamp', ''))
                variables[var_name] = events
                continue

            # limit_events(events, count)
            match = re.match(r'limit_events\((\w+),\s*(\d+)\)', expr)
            if match:
                events_var = match.group(1)
                limit = int(match.group(2))
                events = variables.get(events_var, [])
                variables[var_name] = events[:limit]
                continue

            # concat(events1, events2)
            match = re.match(r'concat\((\w+),\s*(\w+)\)', expr)
            if match:
                var1, var2 = match.group(1), match.group(2)
                events1 = variables.get(var1, [])
                events2 = variables.get(var2, [])
                variables[var_name] = events1 + events2
                continue

            # categorize(events, categories) - add $category to events
            match = re.match(r'categorize\((\w+),', expr)
            if match:
                events_var = match.group(1)
                events = variables.get(events_var, [])
                # Add default category to events (simplified - not doing regex matching)
                categorized = []
                for e in events:
                    e_copy = dict(e)
                    e_copy['data'] = dict(e.get('data', {}))
                    e_copy['data']['$category'] = ['Uncategorized']
                    categorized.append(e_copy)
                variables[var_name] = categorized
                continue

            # union_no_overlap(events1, events2)
            match = re.match(r'union_no_overlap\((\w+),\s*(\w+)\)', expr)
            if match:
                var1, var2 = match.group(1), match.group(2)
                events1 = variables.get(var1, [])
                events2 = variables.get(var2, [])
                variables[var_name] = events1 + events2
                continue

            # period_union(events1, events2)
            match = re.match(r'period_union\((\w+),\s*(\w+)\)', expr)
            if match:
                var1, var2 = match.group(1), match.group(2)
                events1 = variables.get(var1, [])
                events2 = variables.get(var2, [])
                variables[var_name] = events1 + events2
                continue

            # split_url_events(events) - simplified
            match = re.match(r'split_url_events\((\w+)\)', expr)
            if match:
                events_var = match.group(1)
                variables[var_name] = variables.get(events_var, [])
                continue

            # Empty array literal: []
            if expr == '[]':
                variables[var_name] = []
                continue

            # Variable reference
            if expr in variables:
                variables[var_name] = variables[expr]
                continue

            # Unknown expression - set to empty
            variables[var_name] = []

    return return_value

@app.route("/api/0/query/", methods=["POST"])
@app.route("/api/0/query", methods=["POST"])
def query():
    """Query endpoint - supports aw-query language"""
    try:
        data = request.json
        timeperiods = data.get('timeperiods', [])
        query_lines = data.get('query', [])

        # Debug logging to file
        _request_log_file.write(f"[QUERY] timeperiods: {timeperiods}\n")
        _request_log_file.write(f"[QUERY] query_lines: {query_lines}\n")
        _request_log_file.flush()

        results = []

        for period in timeperiods:
            start_dt, end_dt = parse_timeperiod(period)
            result = execute_query(query_lines, start_dt, end_dt)
            _request_log_file.write(f"[QUERY] result type: {type(result)}, len={len(result) if isinstance(result, list) else 'N/A'}\n")
            _request_log_file.flush()
            results.append(result)

        _request_log_file.write(f"[QUERY] final results: {len(results)} periods\n")
        _request_log_file.flush()
        return jsonify(results)
    except Exception as e:
        _request_log_file.write(f"[QUERY] Error: {e}\n")
        import traceback
        _request_log_file.write(traceback.format_exc())
        _request_log_file.flush()
        return jsonify([]), 200


# ============================================
# EXPORT/IMPORT ENDPOINTS
# ============================================

@app.route("/api/0/export", methods=["GET"])
def export_all():
    """Export all data"""
    buckets = {}
    for bucket in Bucket.query.all():
        events = Event.query.filter_by(bucket_id=bucket.id).all()
        buckets[bucket.id] = {
            'bucket': bucket.to_dict(),
            'events': [e.to_dict() for e in events]
        }
    return jsonify({'buckets': buckets})


@app.route("/api/0/buckets/<bucket_id>/export", methods=["GET"])
def export_bucket(bucket_id):
    """Export a single bucket"""
    bucket = Bucket.query.get(bucket_id)
    if not bucket:
        return jsonify({"error": "Bucket not found"}), 404

    events = Event.query.filter_by(bucket_id=bucket_id).all()
    return jsonify({
        'bucket': bucket.to_dict(),
        'events': [e.to_dict() for e in events]
    })


# ============================================
# EMPLOYEE/ADMIN ENDPOINTS (Enterprise)
# ============================================

@app.route("/api/0/admin/employees", methods=["GET"])
def get_employees():
    """Get all employees with their devices (admin only)"""
    employees = Employee.query.all()
    result = []
    for emp in employees:
        emp_dict = emp.to_dict()
        # Get devices for this employee
        devices = Device.query.filter_by(employee_id=emp.id).all()
        emp_dict['devices'] = [d.to_dict() for d in devices]
        # Get event stats
        event_count = Event.query.filter_by(employee_id=emp.id).count()
        total_duration = db.session.query(func.sum(Event.duration)).filter_by(employee_id=emp.id).scalar() or 0
        emp_dict['stats'] = {
            'event_count': event_count,
            'total_hours': round(total_duration / 3600, 2)
        }
        result.append(emp_dict)
    return jsonify({"employees": result})


@app.route("/api/0/admin/employees/<employee_id>", methods=["GET"])
def get_employee(employee_id):
    """Get a specific employee with devices"""
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    emp_dict = employee.to_dict()
    devices = Device.query.filter_by(employee_id=employee_id).all()
    emp_dict['devices'] = [d.to_dict() for d in devices]

    # Get detailed stats
    event_count = Event.query.filter_by(employee_id=employee_id).count()
    total_duration = db.session.query(func.sum(Event.duration)).filter_by(employee_id=employee_id).scalar() or 0

    # Get buckets for this employee
    buckets = Bucket.query.filter_by(employee_id=employee_id).all()

    emp_dict['stats'] = {
        'event_count': event_count,
        'total_hours': round(total_duration / 3600, 2),
        'bucket_count': len(buckets)
    }
    emp_dict['buckets'] = [b.to_dict() for b in buckets]

    return jsonify(emp_dict)


@app.route("/api/0/admin/employees", methods=["POST"])
def create_employee():
    """Create a new employee"""
    data = request.json

    # Accept both 'id' and 'employee_id' for flexibility
    employee_id = data.get('id') or data.get('employee_id')
    if not employee_id:
        return jsonify({"error": "Employee ID is required (use 'id' or 'employee_id')"}), 400

    # Check if employee already exists
    existing = Employee.query.get(employee_id)
    if existing:
        return jsonify({"error": "Employee ID already exists"}), 400

    employee = Employee(
        id=employee_id,
        name=data.get('name'),
        email=data.get('email'),
        department=data.get('department'),
        role=data.get('role', 'employee'),
        is_active=data.get('is_active', True)
    )
    db.session.add(employee)
    db.session.commit()
    return jsonify(employee.to_dict()), 201


@app.route("/api/0/admin/employees/<employee_id>", methods=["PUT"])
def update_employee(employee_id):
    """Update an employee"""
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    data = request.json
    if 'name' in data:
        employee.name = data['name']
    if 'email' in data:
        employee.email = data['email']
    if 'department' in data:
        employee.department = data['department']
    if 'role' in data:
        employee.role = data['role']
    if 'is_active' in data:
        employee.is_active = data['is_active']

    db.session.commit()
    return jsonify(employee.to_dict())


@app.route("/api/0/admin/employees/<employee_id>", methods=["DELETE"])
def delete_employee(employee_id):
    """Delete an employee"""
    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    # Delete associated devices
    Device.query.filter_by(employee_id=employee_id).delete()
    db.session.delete(employee)
    db.session.commit()
    return jsonify({"success": True})


# ============================================
# DEVICE ENDPOINTS
# ============================================

@app.route("/api/0/admin/devices", methods=["GET"])
def get_devices():
    """Get all devices"""
    employee_id = request.args.get('employee_id')
    if employee_id:
        devices = Device.query.filter_by(employee_id=employee_id).all()
    else:
        devices = Device.query.all()
    return jsonify({"devices": [d.to_dict() for d in devices]})


@app.route("/api/0/admin/devices", methods=["POST"])
def create_device():
    """Create or update a device"""
    data = request.json
    device_id = data.get('id') or data.get('hostname')

    # Check if device exists
    device = Device.query.get(device_id)
    if device:
        # Update last seen
        device.last_seen = datetime.utcnow()
        if data.get('os_info'):
            device.os_info = data.get('os_info')
        db.session.commit()
        return jsonify(device.to_dict())

    # Create new device
    device = Device(
        id=device_id,
        employee_id=data.get('employee_id'),
        hostname=data.get('hostname'),
        device_type=data.get('device_type', 'desktop'),
        os_info=data.get('os_info'),
        is_active=True
    )
    db.session.add(device)
    db.session.commit()
    return jsonify(device.to_dict()), 201


@app.route("/api/0/admin/devices/<device_id>", methods=["DELETE"])
def delete_device(device_id):
    """Delete a device"""
    device = Device.query.get(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    db.session.delete(device)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/0/admin/events", methods=["GET"])
def get_admin_events():
    """Get events for a specific employee (admin only)"""
    employee_id = request.args.get('employee_id')
    device_id = request.args.get('device_id')
    limit = request.args.get('limit', 100, type=int)

    query = Event.query
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    if device_id:
        query = query.filter_by(device_id=device_id)

    events = query.order_by(Event.timestamp.desc()).limit(limit).all()

    # Calculate stats
    total_duration = sum(e.duration or 0 for e in events)

    return jsonify({
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "total_hours": round(total_duration / 3600, 2)
    })


@app.route("/api/0/admin/stats", methods=["GET"])
def get_admin_stats():
    """Get overall stats or stats for specific employee"""
    employee_id = request.args.get('employee_id')

    if employee_id:
        event_count = Event.query.filter_by(employee_id=employee_id).count()
        total_duration = db.session.query(func.sum(Event.duration)).filter_by(employee_id=employee_id).scalar() or 0
        bucket_count = Bucket.query.filter_by(employee_id=employee_id).count()
        device_count = Device.query.filter_by(employee_id=employee_id).count()
    else:
        event_count = Event.query.count()
        total_duration = db.session.query(func.sum(Event.duration)).scalar() or 0
        bucket_count = Bucket.query.count()
        device_count = Device.query.count()

    return jsonify({
        "event_count": event_count,
        "total_hours": round(total_duration / 3600, 2),
        "bucket_count": bucket_count,
        "device_count": device_count,
        "employee_count": Employee.query.count()
    })


# ============================================
# HEALTH CHECK
# ============================================

@app.route("/api/0/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "backend": "mysql"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }), 500


# ============================================
# ADMIN DASHBOARD WITH EMPLOYEE SELECTOR
# ============================================

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - ActivityWatch Enterprise</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }

        .admin-header {
            background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid #e94560;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
        }

        .admin-header h1 {
            color: #e94560;
            font-size: 18px;
        }

        .employee-selector {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .employee-selector label { color: #888; font-size: 13px; }

        .employee-selector select {
            padding: 6px 12px;
            font-size: 13px;
            border: 1px solid #e94560;
            border-radius: 5px;
            background: #16213e;
            color: #fff;
            cursor: pointer;
            min-width: 250px;
        }

        .stats-bar { display: flex; gap: 15px; align-items: center; }

        .stat-item {
            text-align: center;
            padding: 4px 12px;
            background: rgba(233, 69, 96, 0.1);
            border-radius: 5px;
        }

        .stat-item .value { font-size: 16px; font-weight: bold; color: #e94560; }
        .stat-item .label { font-size: 9px; color: #888; text-transform: uppercase; }

        .btn { padding: 6px 12px; border: none; border-radius: 5px; cursor: pointer; font-size: 12px; }
        .btn-primary { background: #e94560; color: #fff; }
        .btn-success { background: #28a745; color: #fff; }
        .btn-secondary { background: #0f3460; color: #888; }

        .main-container {
            margin-top: 55px;
            display: flex;
            height: calc(100vh - 55px);
        }

        .sidebar {
            width: 280px;
            background: #16213e;
            border-right: 1px solid #0f3460;
            overflow-y: auto;
            padding: 15px;
        }

        .sidebar h3 {
            color: #e94560;
            font-size: 14px;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #0f3460;
        }

        .employee-card {
            background: #1a1a2e;
            border: 1px solid #0f3460;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .employee-card:hover, .employee-card.active {
            border-color: #e94560;
            background: rgba(233, 69, 96, 0.1);
        }

        .employee-card .name { font-weight: bold; font-size: 14px; color: #fff; }
        .employee-card .dept { font-size: 11px; color: #888; margin-top: 2px; }
        .employee-card .devices { font-size: 10px; color: #666; margin-top: 5px; }
        .employee-card .device-item {
            display: inline-block;
            background: #0f3460;
            padding: 2px 6px;
            border-radius: 3px;
            margin: 2px 2px 0 0;
            font-size: 9px;
        }
        .employee-card .stats-mini {
            display: flex;
            gap: 10px;
            margin-top: 8px;
            font-size: 10px;
            color: #888;
        }
        .employee-card .stats-mini span { color: #e94560; font-weight: bold; }

        .content-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .content-header {
            padding: 15px 20px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
        }

        .content-header h2 { color: #fff; font-size: 16px; }
        .content-header .employee-info { color: #888; font-size: 12px; margin-top: 5px; }

        .content-body {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }

        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .data-card {
            background: #16213e;
            border: 1px solid #0f3460;
            border-radius: 8px;
            padding: 15px;
        }

        .data-card h4 {
            color: #e94560;
            font-size: 13px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #0f3460;
        }

        .data-list { list-style: none; }
        .data-list li {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #0f3460;
            font-size: 12px;
        }
        .data-list li:last-child { border-bottom: none; }
        .data-list .app-name { color: #fff; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .data-list .duration { color: #e94560; font-weight: bold; }

        .no-data { color: #666; text-align: center; padding: 20px; font-size: 13px; }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: #16213e;
            padding: 25px;
            border-radius: 10px;
            width: 400px;
            border: 1px solid #e94560;
        }
        .modal-content h2 { color: #e94560; margin-bottom: 15px; font-size: 16px; }
        .modal-content input, .modal-content select {
            width: 100%;
            padding: 8px;
            margin-bottom: 10px;
            border: 1px solid #0f3460;
            border-radius: 5px;
            background: #1a1a2e;
            color: #fff;
            font-size: 13px;
        }
        .modal-buttons { display: flex; gap: 10px; justify-content: flex-end; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="admin-header">
        <h1>Admin Dashboard</h1>

        <div class="stats-bar" id="statsBar">
            <div class="stat-item">
                <div class="value" id="totalEmployees">-</div>
                <div class="label">Employees</div>
            </div>
            <div class="stat-item">
                <div class="value" id="totalDevices">-</div>
                <div class="label">Devices</div>
            </div>
            <div class="stat-item">
                <div class="value" id="totalEvents">-</div>
                <div class="label">Events</div>
            </div>
            <div class="stat-item">
                <div class="value" id="totalHours">-</div>
                <div class="label">Hours</div>
            </div>
        </div>

        <div>
            <button class="btn btn-success" onclick="showAddEmployeeModal()">+ Add Employee</button>
            <button class="btn btn-primary" onclick="showAddDeviceModal()">+ Add Device</button>
        </div>
    </div>

    <div class="main-container">
        <div class="sidebar">
            <h3>Employees</h3>
            <div id="employeeList">Loading...</div>
        </div>

        <div class="content-area">
            <div class="content-header">
                <h2 id="selectedName">Select an Employee</h2>
                <div class="employee-info" id="selectedInfo">Click on an employee from the sidebar to view their activity data</div>
            </div>

            <div class="content-body">
                <div class="data-grid" id="dataGrid">
                    <div class="data-card">
                        <h4>Top Applications</h4>
                        <ul class="data-list" id="topApps">
                            <li class="no-data">Select an employee to view data</li>
                        </ul>
                    </div>
                    <div class="data-card">
                        <h4>Top Window Titles</h4>
                        <ul class="data-list" id="topTitles">
                            <li class="no-data">Select an employee to view data</li>
                        </ul>
                    </div>
                    <div class="data-card">
                        <h4>Devices</h4>
                        <ul class="data-list" id="deviceList">
                            <li class="no-data">Select an employee to view devices</li>
                        </ul>
                    </div>
                    <div class="data-card">
                        <h4>Recent Activity</h4>
                        <ul class="data-list" id="recentActivity">
                            <li class="no-data">Select an employee to view activity</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Add Employee Modal -->
    <div class="modal" id="addEmployeeModal">
        <div class="modal-content">
            <h2>Add New Employee</h2>
            <input type="text" id="empId" placeholder="Employee ID (e.g., emp001)">
            <input type="text" id="empName" placeholder="Full Name">
            <input type="email" id="empEmail" placeholder="Email">
            <input type="text" id="empDept" placeholder="Department">
            <select id="empRole">
                <option value="employee">Employee</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
            </select>
            <div class="modal-buttons">
                <button class="btn btn-secondary" onclick="hideModals()">Cancel</button>
                <button class="btn btn-primary" onclick="saveEmployee()">Save Employee</button>
            </div>
        </div>
    </div>

    <!-- Add Device Modal -->
    <div class="modal" id="addDeviceModal">
        <div class="modal-content">
            <h2>Add New Device</h2>
            <select id="deviceEmpId">
                <option value="">Select Employee</option>
            </select>
            <input type="text" id="deviceId" placeholder="Device ID / Hostname">
            <input type="text" id="deviceHostname" placeholder="Hostname">
            <select id="deviceType">
                <option value="desktop">Desktop</option>
                <option value="laptop">Laptop</option>
                <option value="mobile">Mobile</option>
            </select>
            <input type="text" id="deviceOs" placeholder="OS Info (e.g., Windows 11)">
            <div class="modal-buttons">
                <button class="btn btn-secondary" onclick="hideModals()">Cancel</button>
                <button class="btn btn-primary" onclick="saveDevice()">Save Device</button>
            </div>
        </div>
    </div>

    <script>
        let employees = [];
        let selectedEmployeeId = null;

        // Format duration in hours/minutes
        function formatDuration(seconds) {
            if (seconds < 60) return Math.round(seconds) + 's';
            if (seconds < 3600) return Math.round(seconds / 60) + 'm';
            return (seconds / 3600).toFixed(1) + 'h';
        }

        // Load overall stats
        async function loadOverallStats() {
            try {
                const response = await fetch('/api/0/admin/stats');
                const data = await response.json();
                document.getElementById('totalEmployees').textContent = data.employee_count;
                document.getElementById('totalDevices').textContent = data.device_count;
                document.getElementById('totalEvents').textContent = data.event_count;
                document.getElementById('totalHours').textContent = data.total_hours;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        // Load employees list
        async function loadEmployees() {
            try {
                const response = await fetch('/api/0/admin/employees');
                const data = await response.json();
                employees = data.employees;

                const container = document.getElementById('employeeList');

                if (employees.length === 0) {
                    container.innerHTML = '<div class="no-data">No employees yet. Add one to get started.</div>';
                    return;
                }

                container.innerHTML = employees.map(emp => `
                    <div class="employee-card ${selectedEmployeeId === emp.id ? 'active' : ''}" onclick="selectEmployee('${emp.id}')">
                        <div class="name">${emp.name || emp.id}</div>
                        <div class="dept">${emp.department || 'No Department'} - ${emp.role || 'employee'}</div>
                        <div class="devices">
                            ${(emp.devices || []).map(d => `<span class="device-item">${d.hostname || d.id}</span>`).join('') || '<span class="device-item">No devices</span>'}
                        </div>
                        <div class="stats-mini">
                            <div>Events: <span>${emp.stats?.event_count || 0}</span></div>
                            <div>Hours: <span>${emp.stats?.total_hours || 0}</span></div>
                        </div>
                    </div>
                `).join('');

                // Also populate device modal dropdown
                const deviceEmpSelect = document.getElementById('deviceEmpId');
                deviceEmpSelect.innerHTML = '<option value="">Select Employee</option>' +
                    employees.map(emp => `<option value="${emp.id}">${emp.name || emp.id}</option>`).join('');

            } catch (error) {
                console.error('Error loading employees:', error);
                document.getElementById('employeeList').innerHTML = '<div class="no-data">Error loading employees</div>';
            }
        }

        // Select an employee and load their data
        async function selectEmployee(employeeId) {
            selectedEmployeeId = employeeId;

            // Update UI to show selected
            document.querySelectorAll('.employee-card').forEach(card => {
                card.classList.remove('active');
                if (card.onclick.toString().includes(employeeId)) {
                    card.classList.add('active');
                }
            });

            // Find employee
            const emp = employees.find(e => e.id === employeeId);
            if (!emp) return;

            document.getElementById('selectedName').textContent = emp.name || emp.id;
            document.getElementById('selectedInfo').textContent =
                `${emp.department || 'No Department'} | ${emp.email || 'No Email'} | ${emp.devices?.length || 0} device(s)`;

            // Load employee's activity data
            await loadEmployeeData(employeeId);
        }

        // Load specific employee's data
        async function loadEmployeeData(employeeId) {
            try {
                // Get employee details with buckets
                const empResponse = await fetch(`/api/0/admin/employees/${employeeId}`);
                const empData = await empResponse.json();

                // Get events for this employee
                const eventsResponse = await fetch(`/api/0/admin/events?employee_id=${employeeId}&limit=1000`);
                const eventsData = await eventsResponse.json();

                // Process events to get top apps and titles
                const appDurations = {};
                const titleDurations = {};

                eventsData.events.forEach(event => {
                    const data = event.data || {};
                    const app = data.app || 'Unknown';
                    const title = data.title || 'Unknown';
                    const duration = event.duration || 0;

                    if (app !== 'Unknown') {
                        appDurations[app] = (appDurations[app] || 0) + duration;
                    }
                    if (title !== 'Unknown' && title !== '') {
                        titleDurations[title] = (titleDurations[title] || 0) + duration;
                    }
                });

                // Sort and display top apps
                const topApps = Object.entries(appDurations)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10);

                document.getElementById('topApps').innerHTML = topApps.length > 0
                    ? topApps.map(([app, dur]) => `
                        <li>
                            <span class="app-name">${app}</span>
                            <span class="duration">${formatDuration(dur)}</span>
                        </li>
                    `).join('')
                    : '<li class="no-data">No application data</li>';

                // Sort and display top titles
                const topTitles = Object.entries(titleDurations)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10);

                document.getElementById('topTitles').innerHTML = topTitles.length > 0
                    ? topTitles.map(([title, dur]) => `
                        <li>
                            <span class="app-name" title="${title}">${title.substring(0, 40)}${title.length > 40 ? '...' : ''}</span>
                            <span class="duration">${formatDuration(dur)}</span>
                        </li>
                    `).join('')
                    : '<li class="no-data">No title data</li>';

                // Display devices
                document.getElementById('deviceList').innerHTML = (empData.devices || []).length > 0
                    ? empData.devices.map(d => `
                        <li>
                            <span class="app-name">${d.hostname || d.id}</span>
                            <span class="duration">${d.device_type} | ${d.os_info || 'Unknown OS'}</span>
                        </li>
                    `).join('')
                    : '<li class="no-data">No devices registered</li>';

                // Display recent activity
                const recentEvents = eventsData.events.slice(0, 10);
                document.getElementById('recentActivity').innerHTML = recentEvents.length > 0
                    ? recentEvents.map(e => `
                        <li>
                            <span class="app-name">${e.data?.app || 'Unknown'}</span>
                            <span class="duration">${new Date(e.timestamp).toLocaleTimeString()}</span>
                        </li>
                    `).join('')
                    : '<li class="no-data">No recent activity</li>';

            } catch (error) {
                console.error('Error loading employee data:', error);
            }
        }

        // Modal functions
        function showAddEmployeeModal() {
            document.getElementById('addEmployeeModal').classList.add('active');
        }

        function showAddDeviceModal() {
            document.getElementById('addDeviceModal').classList.add('active');
        }

        function hideModals() {
            document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
        }

        async function saveEmployee() {
            const employee = {
                id: document.getElementById('empId').value,
                name: document.getElementById('empName').value,
                email: document.getElementById('empEmail').value,
                department: document.getElementById('empDept').value,
                role: document.getElementById('empRole').value
            };

            if (!employee.id) {
                alert('Employee ID is required');
                return;
            }

            try {
                const response = await fetch('/api/0/admin/employees', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(employee)
                });

                if (response.ok) {
                    hideModals();
                    loadEmployees();
                    loadOverallStats();
                    // Clear form
                    ['empId', 'empName', 'empEmail', 'empDept'].forEach(id => document.getElementById(id).value = '');
                } else {
                    const err = await response.json();
                    alert('Failed to add employee: ' + (err.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        async function saveDevice() {
            const device = {
                id: document.getElementById('deviceId').value,
                employee_id: document.getElementById('deviceEmpId').value,
                hostname: document.getElementById('deviceHostname').value || document.getElementById('deviceId').value,
                device_type: document.getElementById('deviceType').value,
                os_info: document.getElementById('deviceOs').value
            };

            if (!device.id || !device.employee_id) {
                alert('Device ID and Employee are required');
                return;
            }

            try {
                const response = await fetch('/api/0/admin/devices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(device)
                });

                if (response.ok) {
                    hideModals();
                    loadEmployees();
                    loadOverallStats();
                    // Clear form
                    ['deviceId', 'deviceHostname', 'deviceOs'].forEach(id => document.getElementById(id).value = '');
                } else {
                    alert('Failed to add device');
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }

        // Initialize
        loadOverallStats();
        loadEmployees();
    </script>
</body>
</html>
"""

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with employee selector"""
    return ADMIN_DASHBOARD_HTML


# ============================================
# STATIC FILE SERVING (aw-webui)
# ============================================

@app.route('/')
def serve_index():
    """Serve aw-webui index.html"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Fallback to index.html for SPA routing
    return send_from_directory(app.static_folder, 'index.html')


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("ActivityWatch MySQL Server - Enterprise Edition")
    print("=" * 60)
    print(f"Server: http://127.0.0.1:5601")
    print(f"Hostname: {HOSTNAME}")
    print("")
    print("API Endpoints:")
    print("  GET  /api/0/info           - Server info")
    print("  GET  /api/0/buckets/       - List buckets")
    print("  POST /api/0/buckets/<id>   - Create bucket")
    print("  GET  /api/0/buckets/<id>/events - Get events")
    print("  POST /api/0/buckets/<id>/events - Create events")
    print("  POST /api/0/buckets/<id>/heartbeat - Heartbeat")
    print("")
    print("Admin Endpoints:")
    print("  GET  /api/0/admin/employees - List employees")
    print("  GET  /api/0/admin/events    - Get employee events")
    print("=" * 60)
    # Listen on all interfaces (0.0.0.0) to accept connections from employee machines
    # Change to '127.0.0.1' if you only want local access
    app.run(host='0.0.0.0', port=5601, debug=True)
