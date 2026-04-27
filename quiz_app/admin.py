from django.contrib import admin
from quiz_app.models import Quiz, Question

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "description", "owner", "created_at")
    search_fields = ("title", "description", "owner__username")
    list_filter = ("created_at",)
    ordering = ("-id",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "question_title", "answer")
    search_fields = ("question_title",)
    list_filter = ("quiz",)
    ordering = ("-id",)

