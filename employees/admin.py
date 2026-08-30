from django.contrib import admin

from .models import EmployeeDocument, Employment, RoleHistory

admin.site.register(Employment)
admin.site.register(EmployeeDocument)
admin.site.register(RoleHistory)
