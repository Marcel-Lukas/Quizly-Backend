from django.conf import settings
from django.db import models


class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    url = models.URLField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )

    def __str__(self):
        return self.title or f"Quiz {self.id}"


class Question(models.Model):
    id = models.AutoField(primary_key=True)
    question_title = models.CharField(max_length=100)
    question_options = models.JSONField()
    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    answer = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question_title

