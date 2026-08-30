from django.contrib import admin

from .models import AttendanceRecord, LeaveBalance, LeaveRequest, LeaveType

admin.site.register(AttendanceRecord)
admin.site.register(LeaveType)
admin.site.register(LeaveRequest)
admin.site.register(LeaveBalance)
