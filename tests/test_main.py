# test_main.py

import pytest
from fastapi.testclient import TestClient

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app
import icmplib

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200

def test_ping():
    try:
        icmplib.ping('127.0.0.1')
    except Exception:
        # Skip test if ICMP is not allowed
        return

    response = client.get("/ping/127.0.0.1")
    assert response.status_code == 200
    assert 'delay' in response.json()

    response = client.get("/ping/::1")
    assert response.status_code == 200
    assert 'delay' in response.json()

def test_myip():
    response = client.get("/myip")
    assert response.status_code == 200
    assert response.text