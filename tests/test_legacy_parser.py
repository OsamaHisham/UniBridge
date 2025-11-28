import os
import shutil
import sys
import tempfile
from datetime import date
from decimal import Decimal

# Ensure the package root is on sys.path so pytest can import legacy_parser
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from legacy_parser import PickRecord


def setup_test_data(tmp_path):
    dst = tmp_path / 'LEGACY_CLIENTS_test.dat'
    content = (
        "101^John Doe^2500.00]400.00]12.50^2023-11-01]2023-12-01]2024-01-15\n"
        "102^Jane Smith^150.00]800.00^2024-02-10]2024-03-15\n"
        "103^Alex Chen^9800.00^^2024-04-20\n"
        "104^Lisa Wong^100.00]50.00^2024-05-01]2024-05-15]2024-06-01]2024-06-15\n"
    )
    dst.write_text(content)
    return str(dst)


def test_read_and_extract(tmp_path):
    test_file = setup_test_data(tmp_path)
    PickRecord.DATA_FILE = test_file

    rec = PickRecord.read('101')
    assert rec.record_key == '101'
    assert rec.extract(1) == 'John Doe'
    assert rec.extract(2, 1) == '2500.00'
    assert rec.extract(2, 2) == '400.00'
    assert rec.extract(2, 99) == ''  # non-existent VM
    assert rec.extract(99) == ''  # non-existent attribute


def test_to_json_and_transactions(tmp_path):
    test_file = setup_test_data(tmp_path)
    PickRecord.DATA_FILE = test_file

    rec = PickRecord.read('101')
    j = rec.to_json()
    assert j['client_id'] == '101'
    assert j['client_name'] == 'John Doe'
    # current balance should be last VM (12.50)
    assert j['current_balance'] == '12.50'
    # balances history should respect parsing
    assert j['legacy_balances_history'] == ['2500.00', '400.00', '12.50']
    # transactions pairing
    assert len(j['transactions']) == 3
    assert j['transactions'][0]['amount'] == '2500.00'
    assert j['transactions'][0]['date'] == '2023-11-01'

def test_to_json_first_latest(tmp_path):
    test_file = setup_test_data(tmp_path)
    PickRecord.DATA_FILE = test_file

    rec = PickRecord.read('101')
    j_first = rec.to_json(latest_balance='first')
    assert j_first['current_balance'] == '2500.00'


def test_extract_subvalue():
    # Directly construct a record with subvalues
    # Construct a record with nested VM and SM values: attribute 2 contains values and subvalues
    # Use double slashes to ensure valid string escapes, or use a raw string. Keep explicit escaping.
    raw = 'Name^ValA]ValB\\S1\\S2^100'
    rec = PickRecord('900', raw)
    # attribute 2 does not exist per this construct, create a subvalue exercise
    # For subvalue, we'll use an attribute that contains a VM and SM
    rec.raw_data = 'Name^A]B\\S1\\S2^100'  # Attribute 2 has a VM containing a subvalue
    rec.attributes = rec.raw_data.split(rec.AM)
    # Extract attribute 2, value 2, subvalue 3 should return 'S2'
    sv = rec.extract(2, 2, 3)
    assert sv == 'S2'


def test_update_and_readback(tmp_path):
    test_file = setup_test_data(tmp_path)
    PickRecord.DATA_FILE = test_file

    rec = PickRecord.read('102')
    # Update attribute 1 (name) and attribute 2 (balances)
    rec.update({1: 'Jane Doe', 2: ['999.99', '0.00']})

    rec2 = PickRecord.read('102')
    assert rec2.extract(1) == 'Jane Doe'
    assert rec2.extract(2, 1) == '999.99'
