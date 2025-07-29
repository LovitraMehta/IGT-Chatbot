# Document Q&A Chatbot

A full-stack AI-powered chatbot that answers questions based on your uploaded documents. Built with **React** (frontend) and **Flask** (backend), it supports PDF, DOCX, TXT, and image files, and uses advanced NLP models for context-aware answers. User authentication, chat history, and file uploads are supported.

---

## Features

- **Document Q&A:** Ask questions and get answers strictly from your uploaded documents.
- **Multi-format Uploads:** Supports PDF, DOCX, TXT, PNG, JPG, JPEG.
- **AI-Powered:** Uses [AI21 Jamba Large](https://www.ai21.com/) for answers and [Sentence Transformers](https://www.sbert.net/) for semantic search.
- **User Authentication:** Register and login with email/password.
- **Chat History:** View and continue previous chat sessions.
- **Context Selection:** Choose which documents to use for context.
- **Speech-to-Text & Text-to-Speech:** Voice input and answer playback (browser and backend support).
- **Secure:** Secrets and API keys are never exposed to the frontend.
- **Responsive UI:** Clean, modern, and mobile-friendly interface.

---

## Demo

![Chatbot Screenshot](./screenshot.png)

---

## Project Structure

```
.
├── app.py                # Flask backend
├── .env                  # Environment variables (not committed)
├── igt-chatbot-frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── App.js
│   │   ├── App.css
│   │   └── ...
│   ├── package.json
│   └── ...
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/igt-chatbot.git
cd igt-chatbot
```

---

### 2. Backend Setup (Flask)

#### a. Create and configure your `.env` file

```env
AI21_API_KEY=your_ai21_api_key
MONGO_URI=your_mongodb_connection_string
FLASK_SECRET_KEY=your_flask_secret_key
TESSERACT_PATH=optional_path_to_tesseract
```

**Never commit your `.env` file!**

#### b. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### c. Run the backend

```bash
python app.py
```

The backend will start on `http://127.0.0.1:5000`.

---

### 3. Frontend Setup (React)

```bash
cd igt-chatbot-frontend
npm install
npm start
```

The frontend will start on `http://localhost:3000` and proxy API requests to the backend.

---

## Deployment

### Backend

- Deploy your Flask app to [Render](https://render.com/), [Railway](https://railway.app/), [Heroku](https://heroku.com/), or any cloud provider that supports Python.
- Set your environment variables (AI21_API_KEY, MONGO_URI, etc.) in the provider's dashboard.

### Frontend

- Deploy the React app to [Vercel](https://vercel.com/), [Netlify](https://netlify.com/), or [GitHub Pages](https://pages.github.com/) (static only).
- **Note:** If using GitHub Pages, you must point API calls to your deployed backend URL (update `API_BASE` in `src/api.js`).

---

## Environment Variables

| Variable           | Description                                 | Where to set                |
|--------------------|---------------------------------------------|-----------------------------|
| `AI21_API_KEY`     | Your AI21 Jamba API key                     | `.env` (backend)            |
| `MONGO_URI`        | MongoDB connection string                   | `.env` (backend)            |
| `FLASK_SECRET_KEY` | Flask session secret                        | `.env` (backend)            |
| `TESSERACT_PATH`   | (Optional) Path to Tesseract executable     | `.env` (backend, Windows)   |

---

## Usage

1. **Register/Login:** Use your email and password to register or log in.
2. **Upload Documents:** Upload PDF, DOCX, TXT, or image files.
3. **Ask Questions:** Type or speak your question. The bot answers using only your documents.
4. **Chat History:** View or continue previous chats from the sidebar.
5. **Context Selection:** Choose which documents to use for context.

---

## Security

- `.env` is in `.gitignore` and **never committed**.
- All secrets are set as environment variables on the backend or in your deployment platform's dashboard.
- Frontend never sees your API keys or database credentials.

---

## Customization

- **Change AI Model:** Edit the model in `app.py` (`jamba-large`).
- **Add File Types:** Update `ALLOWED_EXTENSIONS` and `extract_text()` in `app.py`.
- **UI Tweaks:** Edit `App.css` and React components in `src/components/`.

---

## Troubleshooting

- **LF/CRLF Warnings:**  
  These are safe to ignore on Windows. To avoid them:
  ```bash
  git config --global core.autocrlf true
  ```

- **API Errors:**  
  Ensure your backend is running and `API_BASE` in `src/api.js` points to the correct URL.

- **MongoDB Connection:**  
  Make sure your `MONGO_URI` is correct and your database is accessible.

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss your ideas.

---

## License

[MIT](LICENSE)

---

## Credits

- [AI21 Labs](https://www.ai21.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [Flask](https://flask.palletsprojects.com/)
- [React](https://react.dev/)
- [MongoDB](https://www.mongodb.com/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [gTTS](https://pypi.org/project/gTTS/)
- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper)

---

## Contact

For questions or support, open an issue or contact [your-email@example.com](mailto:your-email@example.com).
