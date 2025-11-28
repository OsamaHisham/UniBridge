# legacy_parser.py

import os
import shutil
from datetime import datetime
from decimal import Decimal, InvalidOperation


class PickRecord:
    """
    A class that simulates a Pick/Universe Dynamic Array record.
    It provides 1-based indexing extraction logic (mimicking Unibasic).
    """
    # Define the primary Pick system delimiters as constants
    AM = '^'  # Attribute Mark (Simulates field separation)
    VM = ']'  # Value Mark (Simulates multi-value separation within a field)
    SM = '\\'  # SubValue Mark (Simulates nested values within a value)
    
    # Path to the simulated legacy data file
    # os.path.dirname(__file__) ensures the file path is correct relative to this module
    DATA_FILE = os.path.join(os.path.dirname(__file__), 'LEGACY_CLIENTS.dat')

    def __init__(self, record_key=None, raw_data=None):
        self.record_key = record_key
        self.raw_data = raw_data
        self.attributes = []
        if raw_data:
            # Split the raw string into attributes using the Attribute Mark (AM)
            self.attributes = raw_data.split(self.AM)

    @classmethod
    def read(cls, record_key):
        """Simulates the Unibasic 'READ' statement, retrieving a record by its key."""
        try:
            with open(cls.DATA_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    # A Pick record is identified by its key at the beginning of the line
                    # The line must be non-empty and start with the key followed by the delimiter
                    if line and line.startswith(f"{record_key}{cls.AM}"):
                        # Split the line once by AM and take the second part (the raw attributes)
                        # e.g., '101^John Doe...' -> 'John Doe...'
                        raw_attributes = line.split(cls.AM, 1)[1]
                        return cls(record_key, raw_attributes)
            return cls(record_key, None) # Record not found
        except FileNotFoundError:
            print(f"Error: Legacy data file not found at {cls.DATA_FILE}")
            return cls(record_key, None)

    def extract(self, attribute_pos, value_pos=None, subvalue_pos=None):
        """
        Simulates the Unibasic 'EXTRACT' function: REC<A> or REC<A, V>.
        Uses 1-based indexing for Attributes (A) and Values (V).
        """
        # Convert 1-based index (Pick Basic convention) to 0-based index (Python convention)
        attr_index = attribute_pos - 1

        try:
            if 0 <= attr_index < len(self.attributes):
                attr = self.attributes[attr_index]
                
                # Check for an empty attribute (e.g., '^^')
                if not attr:
                    return ""

                if value_pos:
                    # Handle Multi-Values (VM delimiter)
                    values = attr.split(self.VM)
                    value_index = value_pos - 1
                    if 0 <= value_index < len(values):
                        # Handle SubValues if required
                        val = values[value_index]
                        if subvalue_pos:
                            svs = val.split(self.SM)
                            sindex = subvalue_pos - 1
                            if 0 <= sindex < len(svs):
                                return svs[sindex]
                            return ""
                        return val
                    else:
                        return "" # Value not found (e.g., REC<2, 99>)
                
                return attr # Return the full attribute string (if no value_pos specified)
            else:
                return "" # Attribute not found (e.g., REC<99>)
        except Exception:
            return ""

    def to_json(self, parse_numbers=True, parse_dates=True, latest_balance='last'):
        """Converts the parsed Dynamic Array data into a standard JSON dictionary."""
        if not self.raw_data:
            return None # Record not found

        # Convert and type cast dynamic-array fields into structured JSON
        balances_raw = self.extract(2)
        dates_raw = self.extract(3)

        balances = [b for b in (balances_raw.split(self.VM) if balances_raw else []) if b != '']
        dates = [d for d in (dates_raw.split(self.VM) if dates_raw else []) if d != '']

        # Try to parse numeric balances when possible
        parsed_balances = []
        for b in balances:
            try:
                parsed_balances.append(Decimal(b) if parse_numbers else b)
            except (InvalidOperation, TypeError):
                parsed_balances.append(b)

        # Try to parse dates in ISO 'YYYY-MM-DD' format
        parsed_dates = []
        for d in dates:
            try:
                parsed_dates.append(datetime.strptime(d, "%Y-%m-%d").date() if parse_dates else d)
            except (ValueError, TypeError):
                parsed_dates.append(d)

        # Pair up balances and dates into transactions list
        transactions = []
        length = max(len(parsed_balances), len(parsed_dates))
        for i in range(length):
            tx = {}
            if i < len(parsed_balances):
                tx["amount"] = parsed_balances[i]
            if i < len(parsed_dates):
                tx["date"] = parsed_dates[i]
            transactions.append(tx)

        # Support choice for latest semantics: 'last' or 'first'
        if parsed_balances:
            if latest_balance == 'first':
                current_balance = parsed_balances[0]
            else:
                current_balance = parsed_balances[-1]
        else:
            current_balance = None

        return {
            "client_id": self.record_key,
            "client_name": self.extract(1),  # Attribute 1: Name
            "current_balance": str(current_balance) if current_balance is not None else None,
            "legacy_balances_history": [str(x) for x in parsed_balances],
            "transaction_dates": [str(x) for x in parsed_dates],
            "transactions": [{"amount": str(t.get('amount')), "date": str(t.get('date'))}
                              for t in transactions],
            "data_source": "Simulated Universe/Pick Flat File"
        }

    def update(self, attribute_map):
        """Update attributes for this record in the flat file.

        attribute_map: dict: keys are attribute positions (1-based ints), values are either string
        or lists (for VM). This function will build an updated attribute string and replace the
        existing record line in the data file.
        """
        if not self.record_key:
            raise ValueError("No record_key available to update")
        # Build attributes list from current attributes
        attrs = list(self.attributes)
        max_index = max((k for k in attribute_map), default=0)
        if max_index > len(attrs):
            # extend with empty strings
            attrs.extend([''] * (max_index - len(attrs)))

        for k, v in attribute_map.items():
            idx = k - 1
            if isinstance(v, (list, tuple)):
                attrs[idx] = self.VM.join([str(x) for x in v])
            else:
                attrs[idx] = str(v)

        new_raw = self.AM.join(attrs)

        # Ensure we create a backup before modifying (safety)
        bak_file = self.DATA_FILE + '.bak'
        shutil.copy(self.DATA_FILE, bak_file)

        updated_line = f"{self.record_key}{self.AM}{new_raw}\n"
        # Rebuild file by replacing the matched line
        with open(self.DATA_FILE, 'r') as f:
            lines = f.readlines()
        with open(self.DATA_FILE, 'w') as f:
            for line in lines:
                if line.strip().startswith(f"{self.record_key}{self.AM}"):
                    f.write(updated_line)
                else:
                    f.write(line)

        # Update our in-memory raw_data and attributes
        self.raw_data = new_raw
        self.attributes = new_raw.split(self.AM)
