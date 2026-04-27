import json
import logging
import os

import whisper
import yt_dlp
from google import genai

from django.conf import settings

from quiz_app.models import Question

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_LENGTH = 12000


def download_audio_from_url(url: str, quiz_id: int = None) -> dict:
    if not url:
        return {"success": False, "error": "No URL provided."}

    output_dir = os.path.join(settings.BASE_DIR, "quiz_app", "media")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"quiz_{quiz_id or 'temp'}_%(id)s.%(ext)s"
    outtmpl = os.path.join(output_dir, filename)

    ydl_opts = {
        **settings.YDL_BASE_OPTS,
        "outtmpl": outtmpl,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = os.path.normpath(ydl.prepare_filename(info))

        return {
            "success": True,
            "filepath": filepath,
            "title": info.get("title"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def run_whisper_transcription(audio_path: str) -> str:
    audio_path = os.path.abspath(audio_path)

    try:
        model = whisper.load_model("small")
        result = model.transcribe(audio_path, language="de")
        os.remove(audio_path)
        return result["text"]
    except Exception as e:
        logger.error("Whisper transcription failed: %s", e)
        return ""


def generate_quiz_with_gemini(transcript: str) -> dict:
    if not transcript.strip():
        return {"title": "Fehler", "description": "Kein Transkript vorhanden", "questions": []}

    prompt = f"""
    Create a quiz based on the following video transcript.

    Requirements:
    - Write the quiz in the same language as the transcript.
    - Create exactly 10 multiple-choice questions.
    - Each question must have exactly 4 answer options.
    - The value of "answer" must be exactly one of the strings in "question_options".
    - Return ONLY valid JSON, no markdown, no code blocks, no explanations.
    - Use the following JSON format:

    {{
      "title": "Quiz Title",
      "description": "Brief description",
      "questions": [
        {{
          "question_title": "...",
          "question_options": ["...", "...", "...", "..."],
          "answer": "<one of the four options above>"
        }}
      ]
    }}

    Transcript:
    {transcript[:MAX_TRANSCRIPT_LENGTH]}
    """

    client = genai.Client(api_key=settings.API_KEY)

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )
        raw_output = response.text.strip()

        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(raw_output[start:end])
            raise ValueError("Gemini output was not valid JSON.")

    except Exception as e:
        logger.error("Gemini generation failed: %s", e)
        return {
            "title": "Failed Generation",
            "description": str(e),
            "questions": [],
        }


def generate_quiz_data_from_video(url: str, quiz_id: int = None) -> dict:
    result = download_audio_from_url(url, quiz_id=quiz_id)
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "Download failed")}

    audio_path = result.get("filepath")

    transcript = run_whisper_transcription(audio_path)
    if not transcript or not transcript.strip():
        return {"success": False, "error": "Empty or failed transcript"}

    quiz_data = generate_quiz_with_gemini(transcript)

    if not isinstance(quiz_data, dict):
        return {"success": False, "error": "Invalid quiz format from Gemini"}

    questions = quiz_data.get("questions")
    if not questions or not isinstance(questions, list):
        return {"success": False, "error": "No questions generated"}

    for i, q in enumerate(questions):
        if not all(k in q for k in ("question_title", "question_options", "answer")):
            return {"success": False, "error": f"Frage {i} unvollständig"}

    return {"success": True, "data": quiz_data}






