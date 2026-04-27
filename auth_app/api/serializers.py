from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for new user registration.

    Requires a matching `confirmed_password` field and enforces
    uniqueness of the provided email address.
    """
    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'confirmed_password', 'email']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_confirmed_password(self, value):
        """Ensure that `confirmed_password` matches the provided `password`."""
        password = self.initial_data.get('password')
        if password and value and password != value:
            raise serializers.ValidationError('Passwords do not match')
        return value

    def validate_email(self, value):
        """Reject the email address if it is already registered."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists')
        return value

    def create(self, validated_data):
        """
        Create and return a new user instance.

        Removes `confirmed_password` from the data before saving and hashes
        the password using Django's `set_password` helper.
        """
        validated_data.pop('confirmed_password')
        password = validated_data.pop('password')
        account = User(**validated_data)
        account.set_password(password)
        account.save()
        return account


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT token serializer with a unified authentication error message.

    Overrides the default behaviour of `TokenObtainPairSerializer` to return
    a single, non-field-specific error when credentials are invalid, preventing
    username-enumeration through distinct per-field error responses.
    """

    def validate(self, attrs):
        """
        Verify credentials manually to return a single, unified error message
        instead of the per-field errors the parent serializer produces by default.
        """
        username = attrs.get("username")
        password = attrs.get("password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Ungültiger Benutzername oder ungültiges Passwort")

        if not user.check_password(password):
            raise serializers.ValidationError("Ungültiger Benutzername oder ungültiges Passwort")

        return super().validate({"username": user.username, "password": password})

