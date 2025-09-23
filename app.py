from flask import Flask, request, jsonify, abort, render_template, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
import time
from storage import load_notes, save_notes
from models import find_note, validate_note_input

BASE_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.context_processor
def inject_asset_version():
    return { 'asset_version': str(int(time.time())) }

# Aggressively disable Jinja template cache to ensure updates show immediately
app.jinja_env.auto_reload = True
app.jinja_env.cache = {}

@app.route('/notes', methods=['POST'])
def create_note():
    data = request.json
    valid, msg = validate_note_input(data, True)
    if not valid:
        abort(400, description=msg)
    notes = load_notes()
    new_id = max([n['id'] for n in notes], default=0) + 1
    note = {
        "id": new_id,
        "title": data['title'],
        "content": data['content'],
        "tags": data.get('tags', [])
    }
    notes.append(note)
    save_notes(notes)
    return jsonify(note), 201

@app.route('/notes', methods=['GET'])
def list_notes():
    notes = load_notes()
    tag = request.args.get('tag')
    search = request.args.get('search')
    filtered = notes
    if tag:
        filtered = [n for n in filtered if tag in n.get('tags', [])]
    if search:
        filtered = [n for n in filtered if search.lower() in n['title'].lower() or search.lower() in n['content'].lower()]
    return jsonify(filtered), 200

@app.route('/notes/<int:id>', methods=['GET'])
def get_note(id):
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description="Note not found")
    # If the user is a browser (Accept: text/html) or explicitly asks for view=1, render HTML
    accept = request.headers.get('Accept', '')
    view_param = request.args.get('view')
    if (view_param and view_param.lower() in ['1', 'true', 'yes']) or ('text/html' in accept and 'application/json' not in accept):
        return render_template('detail.html', note=note)
    return jsonify(note), 200

@app.route('/notes/<int:id>', methods=['PUT'])
def update_note(id):
    data = request.json
    valid, msg = validate_note_input(data, False)
    if not valid:
        abort(400, description=msg)
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description="Note not found")
    if 'title' in data:
        note['title'] = data['title']
    if 'content' in data:
        note['content'] = data['content']
    if 'tags' in data:
        note['tags'] = data['tags']
    save_notes(notes)
    return jsonify(note), 200

@app.route('/notes/<int:id>', methods=['DELETE'])
def delete_note(id):
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description="Note not found")
    notes = [n for n in notes if n['id'] != id]
    save_notes(notes)
    return jsonify({"message": "Note deleted"}), 200

@app.get('/')
def ui_index():
    notes = load_notes()
    tag = request.args.get('tag')
    search = request.args.get('search')
    filtered = notes
    if tag:
        filtered = [n for n in filtered if tag in n.get('tags', [])]
    if search:
        filtered = [n for n in filtered if search.lower() in n['title'].lower() or search.lower() in n['content'].lower()]
    # Convert dicts to simple objects for templates
    class NoteObj:
        def __init__(self, d):
            self.id = d['id']
            self.title = d['title']
            self.content = d['content']
            self.tags = d.get('tags', [])
    notes_view = [NoteObj(n) for n in filtered]
    return render_template('index.html', notes=notes_view)

@app.get('/new')
def ui_new_note():
    return render_template('form.html', note=None)

@app.post('/new')
def ui_create_note():
    data = {
        'title': request.form.get('title', ''),
        'content': request.form.get('content', ''),
        'tags': [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
    }
    if not data['title']:
        abort(400, description='title is required')
    notes = load_notes()
    new_id = max([n['id'] for n in notes], default=0) + 1
    # handle file uploads
    uploaded_files = request.files.getlist('files')
    attachments = []
    for f in uploaded_files:
        if not f or not f.filename:
            continue
        original_name = f.filename
        safe_name = secure_filename(original_name)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        save_path = os.path.join(UPLOAD_FOLDER, unique_name)
        f.save(save_path)
        attachments.append({
            'original': original_name,
            'file': unique_name,
            'mimetype': f.mimetype or 'application/octet-stream'
        })
    if not data['content'] and not attachments:
        abort(400, description='content or at least one file is required')
    note = { 'id': new_id, 'title': data['title'], 'content': data['content'], 'tags': data.get('tags', []), 'attachments': attachments }
    notes.append(note)
    save_notes(notes)
    return redirect(url_for('ui_index'))

@app.get('/note/<int:id>')
def ui_view_note(id):
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description='Note not found')
    return render_template('detail.html', note=note)

# Fallback pretty view that avoids any conflicts with API routes
@app.get('/view/<int:id>')
def ui_view_note_alt(id):
    return ui_view_note(id)

@app.get('/note/<int:id>/edit')
def ui_edit_note(id):
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description='Note not found')
    return render_template('form.html', note=note)

@app.post('/note/<int:id>/edit')
def ui_update_note(id):
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description='Note not found')
    title = request.form.get('title')
    content = request.form.get('content')
    tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
    data = {'title': title, 'content': content, 'tags': tags}
    if not title:
        abort(400, description='title is required')
    # new uploads
    uploaded_files = request.files.getlist('files')
    if uploaded_files:
        attachments = note.get('attachments', [])
        for f in uploaded_files:
            if not f or not f.filename:
                continue
            original_name = f.filename
            safe_name = secure_filename(original_name)
            unique_name = f"{uuid.uuid4().hex}_{safe_name}"
            save_path = os.path.join(UPLOAD_FOLDER, unique_name)
            f.save(save_path)
            attachments.append({ 'original': original_name, 'file': unique_name, 'mimetype': f.mimetype or 'application/octet-stream' })
        note['attachments'] = attachments
    note['title'] = title
    note['content'] = content
    note['tags'] = tags
    save_notes(notes)
    return redirect(url_for('ui_index'))

@app.post('/note/<int:id>/delete')
def ui_delete_note(id):
    notes = load_notes()
    note = find_note(notes, id)
    if not note:
        abort(404, description='Note not found')
    notes = [n for n in notes if n['id'] != id]
    save_notes(notes)
    return redirect(url_for('ui_index'))

if __name__ == '__main__':
    app.run(debug=True)

# Serve uploaded files
@app.get('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)
