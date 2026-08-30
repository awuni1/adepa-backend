from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from orgs.models import Organisation
from people.models import Person

from .models import User


class MeSerializer(serializers.ModelSerializer):
    person_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role", "organisation", "person_id"]

    def get_person_id(self, obj):
        person = getattr(obj, "person", None)
        return person.id if person else None


class CandidateRegisterSerializer(serializers.Serializer):
    """Signup for the candidate portal — links to the Person a job application
    already created for this (org, email) pair, per §6.4."""

    organisation = serializers.PrimaryKeyRelatedField(queryset=Organisation.objects.all())
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs):
        try:
            attrs["person"] = Person.objects.get(
                organisation=attrs["organisation"], email__iexact=attrs["email"], user__isnull=True
            )
        except Person.DoesNotExist as exc:
            raise serializers.ValidationError(
                "No application found for this email. Apply to a job first."
            ) from exc
        return attrs

    def create(self, validated_data):
        person = validated_data["person"]
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            role=User.Role.CANDIDATE,
            organisation=validated_data["organisation"],
            first_name=person.first_name,
            last_name=person.last_name,
        )
        person.user = user
        person.save(update_fields=["user"])
        return user
