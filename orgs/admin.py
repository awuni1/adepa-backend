from django.contrib import admin

from .models import Announcement, Department, Organisation, PolicyDocument

admin.site.register(Organisation)
admin.site.register(Department)
admin.site.register(Announcement)
admin.site.register(PolicyDocument)
