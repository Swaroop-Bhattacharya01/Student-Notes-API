def find_note(notes, id):
    return next((note for note in notes if note["id"] == id), None)

def validate_note_input(data, require_all_fields=True):
    if not data:
        return False, "Input data missing"
    if require_all_fields:
        if 'title' not in data or not isinstance(data.get('title'), str):
            return False, "title is required and must be a string"
        if 'content' not in data or not isinstance(data.get('content'), str):
            return False, "content is required and must be a string"
    else:  # for updates, fields are optional but if present, must be valid type
        if 'title' in data and not isinstance(data.get('title'), str):
            return False, "title must be a string"
        if 'content' in data and not isinstance(data.get('content'), str):
            return False, "content must be a string"
        if 'tags' in data and not isinstance(data.get('tags'), list):
            return False, "tags must be a list"
    return True, ""
