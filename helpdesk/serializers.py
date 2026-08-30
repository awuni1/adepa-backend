from rest_framework import serializers

from .models import Ticket, TicketComment, TicketType


class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ["id", "organisation", "title"]
        read_only_fields = ["organisation"]


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketComment
        fields = ["id", "ticket", "author", "author_name", "body", "created_at"]
        read_only_fields = ["author"]

    def get_author_name(self, obj):
        return f"{obj.author.first_name} {obj.author.last_name}"


class TicketSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    ticket_type_title = serializers.CharField(source="ticket_type.title", read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id", "organisation", "raised_by", "raised_by_name", "ticket_type", "ticket_type_title",
            "title", "description", "priority", "status", "assigned_to", "assigned_to_name",
            "resolved_at", "comments", "created_at",
        ]
        read_only_fields = ["organisation", "raised_by", "resolved_at"]

    def get_raised_by_name(self, obj):
        return f"{obj.raised_by.first_name} {obj.raised_by.last_name}"

    def get_assigned_to_name(self, obj):
        return f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}" if obj.assigned_to else None
