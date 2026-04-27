from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from quiz_app.models import Question, Quiz

User = get_user_model()

MOCK_PATH = "quiz_app.api.serializers.generate_quiz_data_from_video"
YOUTUBE_URL = "https://www.youtube.com/watch?v=hbKoppvdsrk"

VALID_GENERATION_RESPONSE = {
    "success": True,
    "data": {
        "title": "Neues Quiz",
        "description": "Eine Beschreibung",
        "questions": [
            {
                "question_title": "Warum ist die Banane krumm?",
                "question_options": ["A", "B", "C", "D"],
                "answer": "B",
            }
        ],
    },
}


class QuizBaseTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Test123!",
        )
        self.quiz = Quiz.objects.create(
            title="Test Quiz",
            description="Beschreibung",
            owner=self.user,
            url="https://www.youtube.com/watch?v=example",
        )
        self.list_url = reverse("quiz-list-create")
        self.detail_url = reverse("my-quizzes", args=[self.quiz.id])


class QuizViewsPositiveTest(QuizBaseTestCase):

    @patch(MOCK_PATH)
    def test_create_quiz_authenticated(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = VALID_GENERATION_RESPONSE

        response = self.client.post(self.list_url, {"url": YOUTUBE_URL})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Neues Quiz")
        self.assertEqual(response.data["description"], "Eine Beschreibung")
        self.assertEqual(response.data["video_url"], YOUTUBE_URL)
        self.assertEqual(len(response.data["questions"]), 1)
        quiz = Quiz.objects.get(title="Neues Quiz", owner=self.user)
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 1)

    @patch(MOCK_PATH)
    def test_create_quiz_with_multiple_questions(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = {
            "success": True,
            "data": {
                "title": "Multi Quiz",
                "description": "Viele Fragen",
                "questions": [
                    {"question_title": f"Frage {i}", "question_options": ["A", "B", "C", "D"], "answer": "A"}
                    for i in range(3)
                ],
            },
        }

        response = self.client.post(self.list_url, {"url": YOUTUBE_URL})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        quiz = Quiz.objects.get(title="Multi Quiz", owner=self.user)
        self.assertEqual(Question.objects.filter(quiz=quiz).count(), 3)

    def test_list_quizzes_returns_only_own(self):
        other = User.objects.create_user(
            username="stranger", email="s@example.com", password="pw"
        )
        Quiz.objects.create(title="Fremd Quiz", owner=other, url="https://example.com")
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Quiz")

    def test_retrieve_own_quiz(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Quiz")
        self.assertEqual(response.data["description"], "Beschreibung")
        self.assertIn("questions", response.data)
        self.assertIn("video_url", response.data)

    def test_partial_update_own_quiz(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.detail_url, {"title": "Geänderter Titel"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Geänderter Titel")
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.title, "Geänderter Titel")
        self.assertEqual(self.quiz.description, "Beschreibung")

    def test_partial_update_description(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(self.detail_url, {"description": "Neue Beschreibung"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.quiz.refresh_from_db()
        self.assertEqual(self.quiz.description, "Neue Beschreibung")
        self.assertEqual(self.quiz.title, "Test Quiz")

    def test_delete_own_quiz(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=self.quiz.id).exists())


class QuizViewsNegativeTest(QuizBaseTestCase):

    def setUp(self):
        super().setUp()
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="otherpassword",
        )

    def test_create_quiz_unauthenticated(self):
        response = self.client.post(self.list_url, {"url": YOUTUBE_URL})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_quiz_missing_url(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.list_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("url", response.data)

    @patch(MOCK_PATH)
    def test_create_quiz_generation_failure(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.return_value = {"success": False, "error": "KI nicht erreichbar"}

        response = self.client.post(self.list_url, {"url": YOUTUBE_URL})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(MOCK_PATH)
    def test_create_quiz_generation_exception(self, mock_generate):
        self.client.force_authenticate(user=self.user)
        mock_generate.side_effect = Exception("Verbindungsfehler")

        response = self.client.post(self.list_url, {"url": YOUTUBE_URL})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_quizzes_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_quiz_unauthenticated(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_quiz_unauthenticated(self):
        response = self.client.patch(self.detail_url, {"title": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_quiz_unauthenticated(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_quiz_not_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_quiz_not_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.patch(self.detail_url, {"title": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_quiz_not_owner(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_quiz_with_invalid_field(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.detail_url, {"url": "https://hack.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_nonexistent_quiz(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("my-quizzes", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)





