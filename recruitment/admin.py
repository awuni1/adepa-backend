from django.contrib import admin

from .models import Application, ApplicationNote, JobPosting, Scorecard

admin.site.register(JobPosting)
admin.site.register(Application)
admin.site.register(ApplicationNote)
admin.site.register(Scorecard)
