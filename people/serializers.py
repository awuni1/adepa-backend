from rest_framework import serializers

from .models import Person


class AvatarURLMixin:
    """CloudinaryField serializes to its bare public_id (e.g. "xsnhmb2ku…")
    by default — not a URL — so an <img src> built from it 404s against the
    frontend's own origin instead of loading from Cloudinary. Every
    serializer that exposes `avatar` for reading needs this so the field
    comes back as the real delivery URL instead."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if "avatar" in data and getattr(instance, "avatar", None):
            data["avatar"] = instance.avatar.url
        return data


class PersonSerializer(AvatarURLMixin, serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "id",
            "organisation",
            "user",
            "first_name",
            "last_name",
            "email",
            "phone",
            "avatar",
            "lifecycle_stage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["lifecycle_stage"]
