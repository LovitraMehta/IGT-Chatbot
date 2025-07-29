from flask import jsonify
import os
from dotenv import load_dotenv
from ai21 import AI21Client
from ai21.models.chat import ChatMessage
from pymongo import MongoClient
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
import tempfile
import docx
import PyPDF2
from pdf2image import convert_from_path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from datetime import datetime
import re
from gtts import gTTS
from faster_whisper import WhisperModel
import io
from PIL import Image
import pytesseract
from flask_cors import CORS
import bcrypt
import markdown

load_dotenv()

# Configure Tesseract path if needed
if os.getenv('TESSERACT_PATH'):
    pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT_PATH')

api_key = os.getenv('AI21_API_KEY')
if not api_key:
    raise ValueError("API key not found. Please set AI21_API_KEY in your .env file.")

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["chatbot"]
chats = db["chats"]

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'png', 'jpg', 'jpeg'}


app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecret')
CORS(app, supports_credentials=True)

client = AI21Client(api_key=api_key)

# Load the embedding model once at startup
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

whisper_model = WhisperModel('medium', device='cpu', compute_type='int8')

def split_into_chunks(text, chunk_size=500):
    paragraphs = text.split('\n')
    chunks = []
    current = ''
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += para + '\n'
        else:
            chunks.append(current.strip())
            current = para + '\n'
    if current:
        chunks.append(current.strip())
    return [c for c in chunks if c.strip()]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file_path, ext):
    if ext == 'txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    elif ext == 'pdf':
        try:
            # First try PyPDF2 for text-based PDFs
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join(page.extract_text() or '' for page in reader.pages)
                if len(text.strip()) > 0:  # If we got meaningful text
                    return text
                
            # Fall back to OCR for scanned PDFs
            pages = convert_from_path(file_path)
            text = ""
            for i, page in enumerate(pages):
                page_text = pytesseract.image_to_string(page)
                text += f"\n--- Page {i+1} ---\n" + page_text
            return text
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return ""
    elif ext == 'docx':
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    elif ext in ('png', 'jpg', 'jpeg'):
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)
    return ''

def is_valid_email(email):
    allowed_domains = ["@gmail.com", "@yahoo.com", "@outlook.com", "@hotmail.com"]
    return any(email.endswith(domain) for domain in allowed_domains)

def is_valid_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[^A-Za-z0-9]', password):
        return False
    return True

EMAIL_AND_CHAT_FORM = '''
<!doctype html>
<title>Chatbot</title>
<h2>Document Q&amp;A Chatbot</h2>
<script>
let mediaRecorder, audioChunks = [];
let answerAudio = null;
let isPlaying = false;
function startRecording() {
  audioChunks = [];
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.wav');
      fetch('/stt', { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
          if (data.text) {
            document.getElementById('question_input').value = data.text;
          } else {
            alert('Transcription failed.');
          }
        });
    };
  });
}
function stopRecording() {
  if (mediaRecorder) mediaRecorder.stop();
}
function playPauseAnswer(btn) {
  const answer = document.getElementById('answer_text');
  if (!answer) return;
  if (!answerAudio) {
    fetch('/tts', { method: 'POST', body: new URLSearchParams({ text: answer.innerText }) })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        answerAudio = new Audio(url);
        answerAudio.onended = () => {
          isPlaying = false;
          btn.innerText = '▶️ Play';
        };
        answerAudio.play();
        isPlaying = true;
        btn.innerText = '⏸ Pause';
      });
  } else if (isPlaying) {
    answerAudio.pause();
    isPlaying = false;
    btn.innerText = '▶️ Play';
  } else {
    answerAudio.play();
    isPlaying = true;
    btn.innerText = '⏸ Pause';
  }
}
</script>
<form method=post enctype=multipart/form-data>
  <label>Email:</label>
  <input type=text name=email placeholder="Email" value="{{ user_email or '' }}" style="width:300px">
  <input type=submit name=action value="Login">
</form>
{% if user_email %}
  <form method=post enctype=multipart/form-data>
    <input type=file name=files multiple>
    <input type=submit name=action value="Upload">
  </form>
  {% if uploaded_files %}
    <form method=post>
      <label>Choose context:</label>
      <div style="margin-bottom:10px;">
        <input type=radio name=context_mode value="global" id="ctx_global" {% if context_mode == 'global' %}checked{% endif %}>
        <label for="ctx_global">Global Context</label>
        <input type=radio name=context_mode value="document" id="ctx_document" {% if context_mode == 'document' %}checked{% endif %}>
        <label for="ctx_document">Single Document</label>
        <input type=radio name=context_mode value="custom" id="ctx_custom" {% if context_mode == 'custom' %}checked{% endif %}>
        <label for="ctx_custom">Custom Selection</label>
      </div>
      {% if context_mode == 'document' %}
        <label>Select document:</label>
        <select name="selected_doc">
          {% for fname in uploaded_files %}
            <option value="{{ fname }}" {% if fname == selected_doc %}selected{% endif %}>{{ fname }}</option>
          {% endfor %}
        </select>
      {% elif context_mode == 'custom' %}
        <label>Select documents:</label><br>
        {% for fname in uploaded_files %}
          <input type="checkbox" name="selected_docs" value="{{ fname }}" {% if selected_docs and fname in selected_docs %}checked{% endif %}> {{ fname }}<br>
        {% endfor %}
        <br><small>You can select any number of documents.</small>
      {% endif %}
      <br>
      <input type=text name=question id="question_input" style="width:400px">
      <button type="button" onclick="startRecording(); this.disabled=true; document.getElementById('stopBtn').disabled=false;">🎤 Start Recording</button>
      <button type="button" id="stopBtn" onclick="stopRecording(); this.disabled=true; document.querySelector('[onclick^=startRecording]').disabled=false;" disabled>⏹ Stop</button>
      <input type=submit name=action value="Ask">
    </form>
  {% endif %}
{% endif %}
{% if chat_history %}
  <h3>Chat History</h3>
  <ul>
  {% for q, a in chat_history %}
    <li><b>You:</b> {{ q }}<br><b>AI:</b> {{ a }}</li>
  {% endfor %}
  </ul>
{% endif %}
{% if answer %}
  <h3>Answer:</h3>
  <div id="answer_text" style="background:#dfd;padding:10px">{{ answer_html|safe }}</div>
  <button type="button" id="playPauseBtn" onclick="playPauseAnswer(this)">▶️ Play</button>
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    user_email = session.get('user_email')
    chat_pairs = session.get('current_chat', [])
    answer = chat_pairs[-1][1] if chat_pairs else None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'Login':
            email = request.form.get('email', '').strip().lower()
            if not is_valid_email(email):
                flash('Invalid email. Please enter a valid Gmail, Yahoo, Outlook, or Hotmail address.')
                return render_template_string(EMAIL_AND_CHAT_FORM, user_email=None, chat_history=[], answer=None)
            session.clear()
            session['user_email'] = email
            user_chat = chats.find_one({"user_id": email, "history": {"$exists": True}})
            if user_chat:
                session['current_chat'] = [(h['content'], user_chat['history'][i+1]['content'])
                    for i, h in enumerate(user_chat['history']) if h['role'] == 'user' and i+1 < len(user_chat['history']) and user_chat['history'][i+1]['role'] == 'assistant']
            else:
                session['current_chat'] = []
                chats.insert_one({"user_id": email, "history": []})
            return render_template_string(EMAIL_AND_CHAT_FORM, user_email=email, chat_history=session['current_chat'], answer=None)
        elif action == 'Upload' and user_email:
            files = request.files.getlist('files')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    ext = filename.rsplit('.', 1)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.'+ext) as tmp:
                        file.save(tmp.name)
                        try:
                            text = extract_text(tmp.name, ext)
                            if not text.strip():
                                flash(f'Warning: Could not extract text from {filename}')
                                continue
                        except Exception as e:
                            flash(f'Error processing {filename}: {str(e)}')
                            continue
                    os.unlink(tmp.name)
                    chunks = split_into_chunks(text)
                    embeddings = embedding_model.encode(chunks).tolist()
                    doc_data = [{"chunk": chunk, "embedding": emb} for chunk, emb in zip(chunks, embeddings)]
                    chats.insert_one({
                        "user_id": user_email,
                        "filename": filename,
                        "upload_date": datetime.utcnow(),
                        "document_chunks": doc_data
                    })
            flash('Files uploaded and processed successfully.')
            uploaded_files = [d['filename'] for d in chats.find({"user_id": user_email, "filename": {"$exists": True}}, {"filename": 1}) if 'filename' in d]
            context_mode = 'document' if uploaded_files else 'global'
            selected_doc = uploaded_files[0] if uploaded_files else None
            return render_template_string(EMAIL_AND_CHAT_FORM, user_email=user_email, chat_history=chat_pairs, answer=answer, uploaded_files=uploaded_files, context_mode=context_mode, selected_doc=selected_doc)
        elif action == 'Ask' and user_email:
            question = request.form.get('question', '')
            context_mode = request.form.get('context_mode', 'global')
            selected_doc = request.form.get('selected_doc')
            selected_docs = request.form.getlist('selected_docs')
            uploaded_files = [d['filename'] for d in chats.find({"user_id": user_email, "filename": {"$exists": True}}, {"filename": 1}) if 'filename' in d]
            if context_mode == 'document' and selected_doc:
                pipeline = [
                    {"$match": {"user_id": user_email, "filename": selected_doc}},
                    {"$unwind": "$document_chunks"},
                    {"$project": {
                        "chunk": "$document_chunks.chunk",
                        "embedding": "$document_chunks.embedding",
                        "filename": 1,
                        "upload_date": 1
                    }}
                ]
            elif context_mode == 'custom' and selected_docs:
                pipeline = [
                    {"$match": {"user_id": user_email, "filename": {"$in": selected_docs}}},
                    {"$unwind": "$document_chunks"},
                    {"$project": {
                        "chunk": "$document_chunks.chunk",
                        "embedding": "$document_chunks.embedding",
                        "filename": 1,
                        "upload_date": 1
                    }}
                ]
            else:
                pipeline = [
                    {"$match": {"user_id": user_email}},
                    {"$unwind": "$document_chunks"},
                    {"$project": {
                        "chunk": "$document_chunks.chunk",
                        "embedding": "$document_chunks.embedding",
                        "filename": 1,
                        "upload_date": 1
                    }}
                ]
            results = list(chats.aggregate(pipeline))
            if not results:
                flash('Please upload a document first.')
                return render_template_string(EMAIL_AND_CHAT_FORM, user_email=user_email, chat_history=chat_pairs, answer=None, uploaded_files=uploaded_files, context_mode=context_mode, selected_doc=selected_doc)
            chunks = [r['chunk'] for r in results]
            embeddings = [r['embedding'] for r in results]
            question_emb = embedding_model.encode([question])[0]
            chunk_embs = np.array(embeddings)
            sims = cosine_similarity([question_emb], chunk_embs)[0]
            top_indices = sims.argsort()[-3:][::-1]
            context_chunks = [chunks[i] for i in top_indices]
            context = '\n'.join(context_chunks)
            system_prompt = (
                "You are a document question answering assistant.\n"
                "You must answer ONLY using the information present in the provided document context below.\n"
                "If the answer is not explicitly present in the document, you MUST reply with: 'The answer is not found in the document.'\n"
                "You are NOT allowed to use any outside knowledge, make assumptions, or provide general information.\n"
                "If the user asks anything not covered in the document, you must reply: 'The answer is not found in the document.'\n"
                "When providing code examples, JSON, or any structured data, always format them using markdown code blocks with appropriate language tags.\n"
                "For example: ```python for code, ```json for JSON, ```javascript for JavaScript, etc.\n\n"
                f"Document Context:\n{context}"
            )
            messages = [
                ChatMessage(role='system', content=system_prompt),
                ChatMessage(role='user', content=question)
            ]
            response = client.chat.completions.create(
                model='jamba-large',
                messages=messages
            )
            ai_message = response.choices[0].message.content
            context_keywords = set()
            for chunk in context_chunks:
                context_keywords.update(re.findall(r'\w+', chunk.lower()))
            answer_keywords = set(re.findall(r'\w+', ai_message.lower()))
            if context_keywords and not (context_keywords & answer_keywords) and "not found in the document" not in ai_message.lower():
                ai_message = "The answer is not found in the document."
            user_chat = chats.find_one({"user_id": user_email})
            history = user_chat["history"] if user_chat and "history" in user_chat else []
            history.append({"role": "user", "content": question, "timestamp": datetime.utcnow()})
            history.append({"role": "assistant", "content": ai_message, "timestamp": datetime.utcnow()})
            chats.update_one({"user_id": user_email}, {"$set": {"history": history}}, upsert=True)
            chat_pairs = session.get('current_chat', [])
            chat_pairs.append((question, ai_message))
            session['current_chat'] = chat_pairs
            session['context_mode'] = context_mode
            session['selected_doc'] = selected_doc
            session['selected_docs'] = selected_docs
            return render_template_string(EMAIL_AND_CHAT_FORM, user_email=user_email, chat_history=chat_pairs, answer=ai_message, uploaded_files=uploaded_files, context_mode=context_mode, selected_doc=selected_doc, selected_docs=selected_docs)
    uploaded_files = [d['filename'] for d in chats.find({"user_id": user_email, "filename": {"$exists": True}}, {"filename": 1}) if 'filename' in d] if user_email else []
    context_mode = session.get('context_mode')
    selected_doc = session.get('selected_doc')
    selected_docs = session.get('selected_docs', [])
    if not context_mode:
        if uploaded_files:
            context_mode = 'document'
            selected_doc = uploaded_files[0]
        else:
            context_mode = 'global'
            selected_doc = None
    return render_template_string(EMAIL_AND_CHAT_FORM, user_email=user_email, chat_history=chat_pairs, answer=answer, uploaded_files=uploaded_files, context_mode=context_mode, selected_doc=selected_doc, selected_docs=selected_docs)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/stt', methods=['POST'])
def stt():
    if 'audio' not in request.files:
        return {'error': 'No audio file provided'}, 400
    audio_file = request.files['audio']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        audio_file.save(tmp.name)
        segments, _ = whisper_model.transcribe(tmp.name, vad_filter=True, language='en')
        text = ''.join([seg.text for seg in segments])
    os.unlink(tmp.name)
    return {'text': text}

@app.route('/tts', methods=['POST'])
def tts():
    text = request.form.get('text', '')
    if not text:
        return {'error': 'No text provided'}, 400
    tts = gTTS(text)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return send_file(fp, mimetype='audio/mpeg', as_attachment=False, download_name='answer.mp3')


# --- API ENDPOINTS FOR REACT FRONTEND ---
from flask import jsonify

@app.route('/api/chat', methods=['POST'])
def api_chat():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json() or {}
    question = data.get('question', '')
    context_mode = data.get('context_mode', session.get('context_mode', 'global'))
    selected_doc = data.get('selected_doc', session.get('selected_doc'))
    selected_docs = data.get('selected_docs', session.get('selected_docs', []))
    uploaded_files = [d['filename'] for d in chats.find({"user_id": user_email, "filename": {"$exists": True}}, {"filename": 1}) if 'filename' in d]
    if context_mode == 'document' and selected_doc:
        pipeline = [
            {"$match": {"user_id": user_email, "filename": selected_doc}},
            {"$unwind": "$document_chunks"},
            {"$project": {
                "chunk": "$document_chunks.chunk",
                "embedding": "$document_chunks.embedding",
                "filename": 1,
                "upload_date": 1
            }}
        ]
    elif context_mode == 'custom' and selected_docs:
        pipeline = [
            {"$match": {"user_id": user_email, "filename": {"$in": selected_docs}}},
            {"$unwind": "$document_chunks"},
            {"$project": {
                "chunk": "$document_chunks.chunk",
                "embedding": "$document_chunks.embedding",
                "filename": 1,
                "upload_date": 1
            }}
        ]
    else:
        pipeline = [
            {"$match": {"user_id": user_email}},
            {"$unwind": "$document_chunks"},
            {"$project": {
                "chunk": "$document_chunks.chunk",
                "embedding": "$document_chunks.embedding",
                "filename": 1,
                "upload_date": 1
            }}
        ]
    results = list(chats.aggregate(pipeline))
    if not results:
        return jsonify({'error': 'Please upload a document first.'}), 400
    chunks = [r['chunk'] for r in results]
    embeddings = [r['embedding'] for r in results]
    question_emb = embedding_model.encode([question])[0]
    chunk_embs = np.array(embeddings)
    sims = cosine_similarity([question_emb], chunk_embs)[0]
    top_indices = sims.argsort()[-3:][::-1]
    context_chunks = [chunks[i] for i in top_indices]
    context = '\n'.join(context_chunks)
    system_prompt = (
        "You are a document question answering assistant.\n"
        "You must answer ONLY using the information present in the provided document context below.\n"
        "If the answer is not explicitly present in the document, you MUST reply with: 'The answer is not found in the document.'\n"
        "You are NOT allowed to use any outside knowledge, make assumptions, or provide general information.\n"
        "If the user asks anything not covered in the document, you must reply: 'The answer is not found in the document.'\n"
        "When providing code examples, JSON, or any structured data, always format them using markdown code blocks with appropriate language tags.\n"
        "For example: ```python for code, ```json for JSON, ```javascript for JavaScript, etc.\n\n"
        f"Document Context:\n{context}"
    )
    messages = [
        ChatMessage(role='system', content=system_prompt),
        ChatMessage(role='user', content=question)
    ]
    response = client.chat.completions.create(
        model='jamba-large',
        messages=messages
    )
    ai_message = response.choices[0].message.content
    context_keywords = set()
    for chunk in context_chunks:
        context_keywords.update(re.findall(r'\w+', chunk.lower()))
    answer_keywords = set(re.findall(r'\w+', ai_message.lower()))
    if context_keywords and not (context_keywords & answer_keywords) and "not found in the document" not in ai_message.lower():
        ai_message = "The answer is not found in the document."
    user_chat = chats.find_one({"user_id": user_email})
    history = user_chat["history"] if user_chat and "history" in user_chat else []
    history.append({"role": "user", "content": question, "timestamp": datetime.utcnow()})
    history.append({"role": "assistant", "content": ai_message, "timestamp": datetime.utcnow()})
    chats.update_one({"user_id": user_email}, {"$set": {"history": history}}, upsert=True)
    chat_pairs = session.get('current_chat', [])
    chat_pairs.append((question, ai_message))
    session['current_chat'] = chat_pairs
    session['context_mode'] = context_mode
    session['selected_doc'] = selected_doc
    session['selected_docs'] = selected_docs
    # Convert ai_message to HTML using markdown
    ai_message_html = markdown.markdown(ai_message, extensions=['fenced_code', 'tables'])
    return jsonify({'answer': ai_message, 'answer_html': ai_message_html})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    files = request.files.getlist('files')
    uploaded = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.'+ext) as tmp:
                file.save(tmp.name)
                try:
                    text = extract_text(tmp.name, ext)
                    if not text.strip():
                        continue
                except Exception as e:
                    continue
            os.unlink(tmp.name)
            chunks = split_into_chunks(text)
            embeddings = embedding_model.encode(chunks).tolist()
            doc_data = [{"chunk": chunk, "embedding": emb} for chunk, emb in zip(chunks, embeddings)]
            chats.insert_one({
                "user_id": user_email,
                "filename": filename,
                "upload_date": datetime.utcnow(),
                "document_chunks": doc_data
            })
            uploaded.append(filename)
    return jsonify({'uploaded': uploaded})

@app.route('/api/history', methods=['GET'])
def api_history():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    user_chat = chats.find_one({"user_id": user_email, "history": {"$exists": True}})
    chat_pairs = []
    if user_chat and 'history' in user_chat:
        history = user_chat['history']
        for i, h in enumerate(history):
            if h['role'] == 'user' and i+1 < len(history) and history[i+1]['role'] == 'assistant':
                chat_pairs.append({
                    'user': h['content'],
                    'assistant': history[i+1]['content']
                })
    return jsonify({'history': chat_pairs})


# Registration endpoint
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    dob = data.get('dob', '').strip()
    password = data.get('password', '')
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email'}), 400
    if not name or not dob:
        return jsonify({'error': 'Name and date of birth required'}), 400
    if not is_valid_password(password):
        return jsonify({'error': 'Password must be at least 8 characters, include uppercase, lowercase, number, and special character.'}), 400
    user = chats.find_one({"user_id": email})
    if user:
        return jsonify({'error': 'User already exists'}), 400
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    chats.insert_one({
        "user_id": email,
        "name": name,
        "dob": dob,
        "password": hashed_pw,
        "history": []
    })
    session.clear()
    session['user_email'] = email
    session['user_name'] = name
    return jsonify({'success': True, 'name': name})

# Login endpoint
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email'}), 400
    user = chats.find_one({"user_id": email})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if 'password' not in user:
        return jsonify({'error': 'User has no password set. Please register again.'}), 400
    if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({'error': 'Incorrect password'}), 401
    session.clear()
    session['user_email'] = email
    session['user_name'] = user.get('name', '')
    return jsonify({'success': True, 'name': user.get('name', '')})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

# --- Uploaded files endpoint for context selection in frontend ---
@app.route('/api/files', methods=['GET'])
def api_files():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    uploaded_files = [d['filename'] for d in chats.find({"user_id": user_email, "filename": {"$exists": True}}, {"filename": 1}) if 'filename' in d]
    return jsonify({'files': uploaded_files})

# --- New Chat and Chat History Endpoints ---
from flask import g

@app.route('/api/new_chat', methods=['POST'])
def api_new_chat():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    user_chat = chats.find_one({"user_id": user_email})
    now = datetime.utcnow()
    # Archive current chat if it exists and is non-empty
    if user_chat and 'history' in user_chat and user_chat['history']:
        started_at = user_chat.get('current_chat_started_at') or user_chat['history'][0].get('timestamp', now)
        ended_at = now
        archive_entry = {
            'history': user_chat['history'],
            'started_at': started_at,
            'ended_at': ended_at
        }
        chats.update_one(
            {"user_id": user_email},
            {"$push": {"chats_history": archive_entry}, "$set": {"history": [], "current_chat_started_at": now}}
        )
    else:
        chats.update_one({"user_id": user_email}, {"$set": {"history": [], "current_chat_started_at": now}}, upsert=True)
    session['current_chat'] = []
    return jsonify({'success': True})

@app.route('/api/chats_history', methods=['GET'])
def api_chats_history():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    user_chat = chats.find_one({"user_id": user_email})
    chats_history = user_chat.get('chats_history', []) if user_chat else []
    # Only return metadata and first/last message for preview
    preview = []
    for chat in chats_history:
        if not chat['history']:
            continue
        first = chat['history'][0]['content'] if chat['history'] else ''
        last = chat['history'][-1]['content'] if chat['history'] else ''
        preview.append({
            'started_at': chat.get('started_at'),
            'ended_at': chat.get('ended_at'),
            'length': len(chat['history']),
            'first': first,
            'last': last
        })
    return jsonify({'chats_history': preview})

@app.route('/api/chats_history/<int:idx>', methods=['GET'])
def api_get_chat_by_index(idx):
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'error': 'Not logged in'}), 401
    user_chat = chats.find_one({"user_id": user_email})
    chats_history = user_chat.get('chats_history', []) if user_chat else []
    if idx < 0 or idx >= len(chats_history):
        return jsonify({'error': 'Invalid chat index'}), 404
    return jsonify({'history': chats_history[idx]['history'], 'started_at': chats_history[idx].get('started_at'), 'ended_at': chats_history[idx].get('ended_at')})

if __name__ == '__main__':
    app.run(debug=True)