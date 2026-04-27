from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'confirmed_password', 'email']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_confirmed_password(self, value):
        password = self.initial_data.get('password')
        if password and value and password != value:
            raise serializers.ValidationError('Passwords do not match')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def create(self, validated_data):
        validated_data.pop('confirmed_password')
        password = validated_data.pop('password')
        account = User(**validated_data)
        account.set_password(password)
        account.save()
        return account


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Verify credentials manually to return a single, unified error message
        # instead of the per-field errors the parent serializer produces by default.
        username = attrs.get("username")
        password = attrs.get("password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Ungültiger Benutzername oder ungültiges Passwort")

        if not user.check_password(password):
            raise serializers.ValidationError("Ungültiger Benutzername oder ungültiges Passwort")

        return super().validate({"username": user.username, "password": password})

