from django.db import transaction
from rest_framework import serializers

from quiz_app.models import Quiz, Question
from quiz_app.utils import generate_quiz_data_from_video

# Shared between QuizSerializer and QuizDetailSerializer to keep field lists in sync.
QUIZ_FIELDS = ["id", "title", "description", "created_at", "updated_at", "video_url", "url", "questions"]


class QuestionSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for individual quiz questions.

    All fields are read-only because questions are generated automatically
    during quiz creation and must not be modified directly via the API.
    """
    class Meta:
        model = Question
        fields = ["id", "question_title", "question_options", "answer"]
        read_only_fields = ["id", "question_title", "question_options", "answer"]


class QuizSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and listing quizzes.

    On write, accepts a `url` field pointing to a video from which quiz content
    is generated automatically. On read, the same field is exposed as `video_url`
    to avoid overloading `url` in the response payload.
    Title, description, and questions are all generated server-side and are
    therefore read-only.
    """
    questions = QuestionSerializer(many=True, read_only=True)
    # 'url' accepts the video URL on write; 'video_url' exposes the same field on read
    # to avoid overloading 'url' in the response payload.
    video_url = serializers.URLField(source="url", read_only=True)
    url = serializers.URLField(write_only=True, required=True)

    class Meta:
        model = Quiz
        fields = QUIZ_FIELDS
        read_only_fields = ["id", "title", "description", "created_at", "updated_at", "video_url", "questions"]

    def create(self, validated_data):
        """
        Generate quiz content from the video URL and persist the result.

        Quiz content is generated from the video before any database writes.
        The quiz and all its questions are then saved in a single atomic
        transaction to ensure consistency. Raises `ValidationError` if the
        owner cannot be determined, the URL is missing, or generation fails.
        """
        request = self.context.get('request')
        owner = validated_data.pop("owner", None)
        if owner is None:
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError({"detail": "Authentifizierung erforderlich"})
            owner = request.user

        video_url = validated_data.pop("url", None)
        if not video_url:
            raise serializers.ValidationError({"url": "URL ist erforderlich"})

        try:
            result = generate_quiz_data_from_video(video_url)
        except Exception as exc:
            raise serializers.ValidationError(
                {"error": "Quiz-Generierung fehlgeschlagen", "details": str(exc)}
            ) from exc

        if not result.get("success"):
            raise serializers.ValidationError(
                {"error": "Quiz-Generierung fehlgeschlagen", "details": result.get("error")}
            )

        quiz_data = result.get("data") or {}
        generated_questions = quiz_data.get("questions") or []

        # Persist the quiz and all questions in one transaction to ensure consistency.
        with transaction.atomic():
            quiz = Quiz.objects.create(
                title=(quiz_data.get("title") or "Wird generiert...")[:100],
                description=quiz_data.get("description", ""),
                url=video_url,
                owner=owner,
            )

            question_instances = [
                Question(
                    quiz=quiz,
                    question_title=q.get("question_title", ""),
                    question_options=q.get("question_options") if isinstance(q.get("question_options"), list) else [],
                    answer=q.get("answer", ""),
                )
                for q in generated_questions
                if isinstance(q, dict)
            ]

            if question_instances:
                Question.objects.bulk_create(question_instances)

        return quiz


class QuizDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating an existing quiz.

    Only `title` and `description` may be changed via PATCH/PUT requests.
    All other fields, including questions and the video URL, are read-only.
    Unknown fields in the request payload are explicitly rejected to give
    clients a clear error instead of a silent no-op.
    """
    questions = QuestionSerializer(many=True, read_only=True)
    video_url = serializers.URLField(source="url", read_only=True)
    url = serializers.URLField(write_only=True, required=True)

    class Meta:
        model = Quiz
        fields = QUIZ_FIELDS
        read_only_fields = ["id", "created_at", "updated_at", "video_url", "questions"]

    def validate(self, attrs):
        """
        Reject any fields that are not allowed for updates.

        DRF silently ignores unknown fields; explicitly reject them so clients
        receive a clear error instead of a silent no-op.
        """
        allowed_fields = {"title", "description"}
        invalid_fields = set(self.initial_data.keys()) - allowed_fields

        if invalid_fields:
            raise serializers.ValidationError({
                "error": (
                    f"Ungültige Felder: {', '.join(invalid_fields)}. "
                    f"Erlaubt sind nur: {', '.join(sorted(allowed_fields))}."
                )
            })

        return attrs

    def update(self, instance, validated_data):
        """Apply the allowed field changes and save the quiz instance."""
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        return instance

