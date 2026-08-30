from django.contrib import admin

from .models import FeedbackNote, PerformanceReview, ReviewCycle

admin.site.register(ReviewCycle)
admin.site.register(PerformanceReview)
admin.site.register(FeedbackNote)
