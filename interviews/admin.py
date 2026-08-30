from django.contrib import admin

from .models import InterviewParticipant, InterviewSession

admin.site.register(InterviewSession)
admin.site.register(InterviewParticipant)
