# Backend – Quizly Quiz Generator

This Quizly backend was developed as part of a learning project to strengthen backend
development skills. It powers an AI-driven quiz platform and is designed to work
seamlessly with an existing frontend. The application provides a fully featured RESTful
API with complete CRUD functionality. Users can submit a YouTube video URL, the backend
then downloads the audio, transcribes it with OpenAI Whisper, and automatically
generates 10 multiple-choice questions using the Google Gemini API.

The corresponding frontend repository can be found here: [Quizly Frontend](https://github.com/Developer-Akademie-Backendkurs/project.Quizly)

---

## 📋 Table of Contents

- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Project Structure](#-project-structure)
- [Authentication](#-authentication)
- [API Endpoints](#-api-endpoints)
  - [Auth](#auth)
  - [Quiz Management](#quiz-management)
- [AI Quiz Generation Pipeline](#-ai-quiz-generation-pipeline)
- [Permissions](#-permissions)
- [CORS Configuration](#-cors-configuration)
- [Running Tests](#-running-tests)
- [Notes](#-notes)
- [Helpful Documentation](#-helpful-documentation)
- [Contact & Support](#-contact--support)

---

## 🛠 Tech Stack

| | |
|---|---|
| Python | 3.12.x |
| Django | 6.0.4 |
| Django REST Framework | 3.17.1 |
| djangorestframework-simplejwt | 5.5.1 |
| django-cors-headers | 4.9.0 |
| OpenAI Whisper | small model |
| Google Gemini API | gemini-2.0-flash |
| yt-dlp | latest |
| Database | SQLite (default) |

---

## 📦 Prerequisites

- Python 3.12 or higher
- `pip` and `venv` (included with Python)
- A Google Gemini API key ([get one here](https://aistudio.google.com/apikey))
- `ffmpeg` installed on your system (required by yt-dlp for audio extraction)
  - Linux: `sudo apt install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Marcel-Lukas/Quizly-Backend.git
cd Quizly-Backend
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**Hint:** The installation may take a few minutes, as it involves downloading OpenAI Whisper and its dependencies, amongst other things.

### 4. Set up environment variables

Create a `.env` file in the project root:

```
SECRET_KEY=your-django-secret-key
API_KEY=your-google-gemini-api-key
```

### 5. Apply database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a superuser (optional)

Required for accessing the Django Admin (`/admin/`).

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/`.

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key used for cryptographic signing |
| `API_KEY` | Google Gemini API key for AI quiz generation |

Both variables are loaded via `python-dotenv` from a `.env` file in the project root.

---

## 📁 Project Structure

```
Quizly/
│
├── core/                         # Django project configuration
│   ├── settings.py               # Global settings (auth, CORS, JWT, DB)
│   ├── urls.py                   # Root URL dispatcher
│   ├── wsgi.py / asgi.py
│
├── auth_app/                     # Authentication & user management
│   ├── authentication.py         # CookieJWTAuthentication (reads JWT from cookies)
│   ├── models.py                 # Uses Django's default User model
│   ├── api/
│   │   ├── views.py              # RegistrationView, Login, Logout, TokenRefresh
│   │   ├── serializers.py        # RegistrationSerializer, CustomTokenObtainPairSerializer
│   │   └── urls.py
│   └── tests/
│       └── test_auth.py
│
├── quiz_app/                     # Quiz management & AI generation
│   ├── models.py                 # Quiz, Question
│   ├── permissions.py            # IsOwner
│   ├── utils.py                  # AI pipeline (yt-dlp → Whisper → Gemini)
│   ├── api/
│   │   ├── views.py              # QuizListCreateView, QuizDetailView
│   │   ├── serializers.py        # QuizSerializer, QuizDetailSerializer, QuestionSerializer
│   │   └── urls.py
│   ├── media/                    # Temporary audio files (auto-cleaned after transcription)
│   └── tests/
│       └── test_quiz.py
│
├── manage.py
├── requirements.txt
└── db.sqlite3                    # SQLite database (auto-generated)
```

---

## 🔐 Authentication

The API uses **JWT Authentication via HttpOnly Cookies** (powered by `djangorestframework-simplejwt`).

Tokens are never exposed in the response body to reduce XSS attack surface. Instead, they are
stored in secure `HttpOnly` cookies:

| Cookie | Content | Lifetime |
|---|---|---|
| `access_token` | JWT access token | 60 minutes |
| `refresh_token` | JWT refresh token | 1 day |

After a successful login, every subsequent request sends the cookies automatically — no manual
`Authorization` header is required.

---

## 🔌 API Endpoints

Base URL: `http://127.0.0.1:8000/api/`

### Auth

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `register/` | No | Register a new user |
| POST | `login/` | No | Log in; sets `access_token` & `refresh_token` cookies |
| POST | `logout/` | No | Log out; deletes both cookies |
| POST | `token/refresh/` | No | Issues a new access token using the refresh cookie |

**Registration request body:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "yourPassword123",
  "confirmed_password": "yourPassword123"
}
```

**Login request body:**

```json
{
  "username": "johndoe",
  "password": "yourPassword123"
}
```

**Login response body:**

```json
{
  "detail": "Login successfully",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

---

### Quiz Management

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| GET | `quizzes/` | Yes | List all quizzes owned by the current user |
| POST | `quizzes/` | Yes | Submit a video URL — AI generates a full quiz |
| GET | `quizzes/{id}/` | Yes (owner) | Retrieve a single quiz with all questions |
| PATCH | `quizzes/{id}/` | Yes (owner) | Update a quiz |
| DELETE | `quizzes/{id}/` | Yes (owner) | Delete a quiz |

**Create quiz request body:**

```json
{
  "url": "https://www.youtube.com/watch?v=example"
}
```

> **Note:** `url` is write-only. The response exposes the same field as `video_url` to avoid
> ambiguity in the response payload.

**Quiz response example:**

```json
{
  "id": 1,
  "title": "Introduction to Python",
  "description": "A quiz about Python fundamentals based on the video.",
  "created_at": "2026-04-27T10:00:00Z",
  "updated_at": "2026-04-27T10:00:00Z",
  "video_url": "https://www.youtube.com/watch?v=example",
  "questions": [
    {
      "id": 1,
      "question_title": "What is Python?",
      "question_options": ["A snake", "A programming language", "A database", "An OS"],
      "answer": "A programming language"
    }
  ]
}
```

---

## 🤖 AI Quiz Generation Pipeline

When a user sends `POST /api/quizzes/` with a video URL, the following pipeline runs
**synchronously** before returning a response:

```
1. yt-dlp       →  Download best-quality audio from the YouTube URL
2. Whisper      →  Transcribe the audio to text (model: "small", language: "de")
3. Gemini API   →  Generate 10 multiple-choice questions from the transcript
4. Database     →  Persist Quiz + Questions in a single atomic transaction
5. Response     →  Return the complete quiz object
```

- The audio file is **deleted immediately** after transcription to free disk space.
- The transcript is **truncated to 12 000 characters** to stay within Gemini's context limit.
- The pipeline runs inside a `transaction.atomic()` block — if any step fails, nothing is written to the database.

---

## 🔒 Permissions

| Permission | Applied to | Description |
|---|---|---|
| `IsAuthenticated` | All endpoints | Only authenticated users may access the API |
| `IsOwner` | Quiz detail (`/quizzes/{id}/`) | Only the creator of a quiz may read, update, or delete it |

---

## 🌐 CORS Configuration

The following origins are whitelisted by default in `settings.py`:

```
http://127.0.0.1:5500
http://localhost:5500
```

These are also added to `CSRF_TRUSTED_ORIGINS`. To allow additional frontend origins, update
both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` in `core/settings.py`.

`CORS_ALLOW_CREDENTIALS = True` is required so browsers include the HttpOnly cookies in
cross-origin requests.

---

## 🐛 Running Tests

Run all tests:

```bash
python manage.py test
```

Tests are organized per application under `<app>/tests/`:

```
auth_app/tests/    — Registration & login
quiz_app/tests/    — Quiz list, quiz detail
```

Test a specific application:

```bash
python manage.py test quiz_app -v 2
```

| Verbosity | Output |
|---|---|
| `-v 0` | Very little output |
| `-v 1` | Standard (default) |
| `-v 2` | Detailed |
| `-v 3` | Very detailed (near debug) |

---

## 📝 Notes

- `DEBUG = True` is set in the current `settings.py`. Before deploying to production,
  set `DEBUG = False` and configure `ALLOWED_HOSTS` accordingly.
- `SECRET_KEY` and `API_KEY` are loaded from a `.env` file. Never commit the `.env` file
  to version control.
- The default database is SQLite (`db.sqlite3`). For production workloads, replace it with
  PostgreSQL or another production-grade database.
- The AI generation pipeline runs synchronously and can take **30–120 seconds** depending on
  video length. For production use, consider offloading this to a background task queue
  (e.g., Celery + Redis).
- Generated audio files are stored temporarily in `quiz_app/media/` and deleted automatically
  after transcription. Ensure this directory is writable.

---

## 🔗 Helpful Documentation

- [Django Documentation](https://docs.djangoproject.com/en/6.0/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/)
- [Django CORS Headers](https://github.com/adamchainz/django-cors-headers)
- [DRF Permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

---

## 📧 Contact & Support

This is a lightweight backend built with Django and should mainly be seen as a
learning project. If you find any bugs or have ideas for improvements, please
open an issue in the repository.

---

[⬆️ Scroll up](#backend--quizly-quiz-generator)
