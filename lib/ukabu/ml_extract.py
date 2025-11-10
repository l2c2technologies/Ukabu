# Copyright (c) 2025 by L2C2 Technologies. All rights reserved.
# 
# For licensing inquiries, contact:
# Indranil Das Gupta <indradg@l2c2.co.in>

"""
ML log extraction module for UKABU WAF.
Extracts training data from nginx access logs.
"""

import re
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import os

class MLExtractor:
    """Extracts machine learning datasets from nginx access logs."""
    
    # nginx log format: combined_enhanced
    # Format: $host $remote_addr - $remote_user [$time_iso8601] "$request" $status $body_bytes_sent
    #         "$http_referer" "$http_user_agent" "$ukabu_status" "$ukabu_decision" "$strike_type"
    #         "$http_x_forwarded_for" "$request_serial" $request_time $upstream_response_time
    #         "$ssl_protocol" "$ssl_cipher"
    
    LOG_PATTERN = re.compile(
        r'(?P<host>\S+) (?P<remote_addr>\S+) - (?P<remote_user>\S+) \[(?P<time_iso8601>[^\]]+)\] '
        r'"(?P<request>[^"]*)" (?P<status>\d+) (?P<body_bytes_sent>\d+) '
        r'"(?P<http_referer>[^"]*)" "(?P<http_user_agent>[^"]*)" '
        r'"(?P<ukabu_status>[^"]*)" "(?P<ukabu_decision>[^"]*)" "(?P<strike_type>[^"]*)" '
        r'"(?P<http_x_forwarded_for>[^"]*)" "(?P<request_serial>[^"]*)" '
        r'(?P<request_time>\S+) (?P<upstream_response_time>\S+) '
        r'"(?P<ssl_protocol>[^"]*)" "(?P<ssl_cipher>[^"]*)"'
    )
    
    DEFAULT_FIELDS = [
        'timestamp', 'ip', 'domain', 'method', 'path', 'status', 
        'ukabu_status', 'user_agent', 'request_time', 
        'upstream_response_time', 'ssl_protocol', 'ssl_cipher', 'request_id'
    ]
    
    def __init__(self, log_path="/var/log/nginx/access.log"):
        self.log_path = log_path
    
    def extract(self, 
                output_path: str,
                format: str = 'json',
                hours: Optional[int] = None,
                days: Optional[int] = None,
                start: Optional[str] = None,
                end: Optional[str] = None,
                domains: Optional[List[str]] = None,
                ukabu_status: Optional[List[str]] = None,
                min_request_time: Optional[float] = None,
                fields: Optional[List[str]] = None,
                verbose: bool = False) -> bool:
        """
        Extract ML dataset from nginx access logs.
        
        Args:
            output_path: Output file path
            format: Output format ('json' or 'csv')
            hours: Extract last N hours
            days: Extract last N days
            start: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            end: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            domains: Filter by domain list
            ukabu_status: Filter by UKABU status codes
            min_request_time: Minimum request time threshold
            fields: Custom field list
            verbose: Verbose output
        
        Returns:
            True if successful
        """
        if not os.path.exists(self.log_path):
            print(f"Error: Log file not found: {self.log_path}")
            return False
        
        # Calculate time range
        time_filter = self._calculate_time_range(hours, days, start, end)
        
        # Use default fields if not specified
        if fields is None:
            fields = self.DEFAULT_FIELDS
        
        # Parse log file
        records = []
        parsed_count = 0
        filtered_count = 0
        
        if verbose:
            print(f"Reading log file: {self.log_path}")
            if time_filter:
                print(f"Time range: {time_filter['start']} to {time_filter['end']}")
            if domains:
                print(f"Filtering domains: {', '.join(domains)}")
            if ukabu_status:
                print(f"Filtering UKABU status: {', '.join(ukabu_status)}")
        
        with open(self.log_path, 'r', errors='ignore') as f:
            for line in f:
                parsed_count += 1
                
                match = self.LOG_PATTERN.match(line)
                if not match:
                    continue
                
                data = match.groupdict()
                
                # Apply filters
                if not self._apply_filters(data, time_filter, domains, ukabu_status, min_request_time):
                    filtered_count += 1
                    continue
                
                # Extract requested fields
                record = self._extract_record(data, fields)
                records.append(record)
                
                if verbose and len(records) % 10000 == 0:
                    print(f"Extracted {len(records)} records...")
        
        if verbose:
            print(f"\nParsed {parsed_count} lines")
            print(f"Filtered out {filtered_count} records")
            print(f"Extracted {len(records)} records")
        
        # Write output
        if format == 'json':
            return self._write_json(output_path, records, verbose)
        elif format == 'csv':
            return self._write_csv(output_path, records, fields, verbose)
        else:
            print(f"Error: Invalid format '{format}', use 'json' or 'csv'")
            return False
    
    def _calculate_time_range(self, hours, days, start, end):
        """Calculate time range for filtering."""
        now = datetime.now()
        
        if hours:
            return {
                'start': now - timedelta(hours=hours),
                'end': now
            }
        elif days:
            return {
                'start': now - timedelta(days=days),
                'end': now
            }
        elif start or end:
            time_range = {}
            if start:
                time_range['start'] = datetime.fromisoformat(start.replace('T', ' '))
            if end:
                time_range['end'] = datetime.fromisoformat(end.replace('T', ' '))
            return time_range
        
        return None
    
    def _apply_filters(self, data, time_filter, domains, ukabu_status, min_request_time):
        """Apply filters to log entry."""
        # Time filter
        if time_filter:
            try:
                # Parse ISO8601 datetime from nginx log
                log_time = datetime.strptime(data['time_iso8601'], '%Y-%m-%dT%H:%M:%S%z')
                log_time = log_time.replace(tzinfo=None)  # Make naive for comparison
                
                if 'start' in time_filter and log_time < time_filter['start']:
                    return False
                if 'end' in time_filter and log_time > time_filter['end']:
                    return False
            except:
                return False
        
        # Domain filter
        if domains and data['host'] not in domains:
            return False
        
        # UKABU status filter
        if ukabu_status:
            status = data.get('ukabu_status', '-')
            if status not in ukabu_status and status != '-':
                return False
        
        # Request time filter
        if min_request_time is not None:
            try:
                req_time = float(data.get('request_time', 0))
                if req_time < min_request_time:
                    return False
            except:
                return False
        
        return True
    
    def _extract_record(self, data, fields):
        """Extract record with requested fields."""
        record = {}
        
        for field in fields:
            if field == 'timestamp':
                record['timestamp'] = data['time_iso8601']
            elif field == 'ip':
                record['ip'] = data['remote_addr']
            elif field == 'domain':
                record['domain'] = data['host']
            elif field == 'method':
                # Extract method from request
                request = data['request']
                parts = request.split(' ', 1)
                record['method'] = parts[0] if parts else '-'
            elif field == 'path':
                # Extract path from request
                request = data['request']
                parts = request.split(' ')
                record['path'] = parts[1] if len(parts) > 1 else '-'
            elif field == 'status':
                record['status'] = int(data['status'])
            elif field == 'ukabu_status':
                record['ukabu_status'] = data['ukabu_status'] if data['ukabu_status'] != '-' else None
            elif field == 'user_agent':
                record['user_agent'] = data['http_user_agent']
            elif field == 'request_time':
                try:
                    record['request_time'] = float(data['request_time'])
                except:
                    record['request_time'] = None
            elif field == 'upstream_response_time':
                try:
                    record['upstream_response_time'] = float(data['upstream_response_time'])
                except:
                    record['upstream_response_time'] = None
            elif field == 'ssl_protocol':
                record['ssl_protocol'] = data['ssl_protocol'] if data['ssl_protocol'] != '-' else None
            elif field == 'ssl_cipher':
                record['ssl_cipher'] = data['ssl_cipher'] if data['ssl_cipher'] != '-' else None
            elif field == 'request_id':
                record['request_id'] = data['request_serial'] if data['request_serial'] != '-' else None
            elif field == 'xff':
                record['xff'] = data['http_x_forwarded_for'] if data['http_x_forwarded_for'] != '-' else None
            elif field == 'referer':
                record['referer'] = data['http_referer'] if data['http_referer'] != '-' else None
        
        return record
    
    def _write_json(self, output_path, records, verbose):
        """Write records to JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(records, f, indent=2)
            
            if verbose:
                print(f"\nâœ“ Wrote {len(records)} records to {output_path}")
            else:
                print(f"âœ“ Extracted {len(records)} records to {output_path}")
            
            # Set secure permissions
            os.chmod(output_path, 0o600)
            
            return True
        except Exception as e:
            print(f"Error writing JSON: {e}")
            return False
    
    def _write_csv(self, output_path, records, fields, verbose):
        """Write records to CSV file."""
        try:
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(records)
            
            if verbose:
                print(f"\nâœ“ Wrote {len(records)} records to {output_path}")
            else:
                print(f"âœ“ Extracted {len(records)} records to {output_path}")
            
            # Set secure permissions
            os.chmod(output_path, 0o600)
            
            return True
        except Exception as e:
            print(f"Error writing CSV: {e}")
            return False
