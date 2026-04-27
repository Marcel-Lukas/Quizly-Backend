from rest_framework import serializers
from django.db import transaction
from quiz_app.models import Quiz, Question
from quiz_app.utils import generate_quiz_data_from_video


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "question_title", "question_options", "answer"]
        read_only_fields = ["id", "question_title", "question_options", "answer"]


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    video_url = serializers.URLField(source="url", read_only=True)
    url = serializers.URLField(write_only=True, required=True)

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "created_at",
                  "updated_at", "video_url", "url", "questions"]
        read_only_fields = ["id", "title", "description", "created_at", "updated_at", "video_url", "questions"]

    def create(self, validated_data):
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
            raise serializers.ValidationError({"error": "Quiz-Generierung fehlgeschlagen", "details": str(exc)}) from exc

        if not result.get("success"):
            raise serializers.ValidationError({"error": "Quiz-Generierung fehlgeschlagen", "details": result.get("error")})

        quiz_data = result.get("data") or {}
        generated_questions = quiz_data.get("questions") or []

        with transaction.atomic():
            quiz = Quiz.objects.create(
                title=(quiz_data.get("title") or "Wird generiert...")[:100],
                description=quiz_data.get("description", ""),
                url=video_url,
                owner=owner,
            )

            question_instances = []
            for q in generated_questions:
                if not isinstance(q, dict):
                    continue

                options = q.get("question_options") or []
                if not isinstance(options, list):
                    options = []

                question_instances.append(
                    Question(
                        quiz=quiz,
                        question_title=q.get("question_title", ""),
                        question_options=options,
                        answer=q.get("answer", ""),
                    )
                )

            if question_instances:
                Question.objects.bulk_create(question_instances)

        return quiz
    


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    video_url = serializers.URLField(source="url", read_only=True)
    url = serializers.URLField(write_only=True, required=True)
    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "created_at", "updated_at", "video_url", "url", "questions"]
        read_only_fields = ["id", "created_at", "updated_at", "video_url", "questions"]

    def validate(self, attrs):
        allowed_fields = {"title", "description"}
        input_fields = set(self.initial_data.keys())
        invalid_fields = input_fields - allowed_fields

        if invalid_fields:
            raise serializers.ValidationError({
                "error": f"Ungültige Felder: {', '.join(invalid_fields)}. "
                         f"Erlaubt sind nur: {', '.join(sorted(allowed_fields))}."
            })

        return attrs

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.save()
        return instance



