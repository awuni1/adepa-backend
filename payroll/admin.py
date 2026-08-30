from django.contrib import admin

from .models import PayoutAccount, PayrollRun, Payslip, SalaryStructure

admin.site.register(SalaryStructure)
admin.site.register(PayrollRun)
admin.site.register(Payslip)
admin.site.register(PayoutAccount)
