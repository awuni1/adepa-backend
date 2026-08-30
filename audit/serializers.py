from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "actor", "actor_name", "model_name", "object_id",
            "object_repr", "action", "changes", "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System"
        return obj.actor.get_full_name() or obj.actor.username
