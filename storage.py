import json
import os

DATA_FILE = 'notes.json'

def load_notes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_notes(notes):
    with open(DATA_FILE, 'w') as f:
        json.dump(notes, f, indent=2)
