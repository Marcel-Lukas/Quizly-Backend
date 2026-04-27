from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from quiz_app.api.serializers import QuizSerializer, QuizDetailSerializer
from quiz_app.models import Quiz
from quiz_app.permissions import IsOwner


class QuizListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizSerializer

    def get_queryset(self):
        return Quiz.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizDetailSerializer
    permission_classes = [IsAuthenticated, IsOwner]

