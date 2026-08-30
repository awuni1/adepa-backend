from django.contrib import admin

from .models import AIScreeningResult, AIUsageLog, AttritionFlag, ChatSession, InterviewArtifact

admin.site.register(AIScreeningResult)
admin.site.register(InterviewArtifact)
admin.site.register(AttritionFlag)
admin.site.register(ChatSession)
admin.site.register(AIUsageLog)
