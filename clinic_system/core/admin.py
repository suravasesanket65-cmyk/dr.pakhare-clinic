from django.contrib import admin
# pyrefly: ignore [missing-import]
from .models import (
    Patients,
    Doctors,
    Appointments,
    Visits,
    Treatments,
    Prescriptions,
    Invoices,
    Payments,
    Staff,
    Users,
    ClinicSettings
)

admin.site.register(Patients)
admin.site.register(Doctors)
admin.site.register(Appointments)
admin.site.register(Visits)
admin.site.register(Treatments)
admin.site.register(Prescriptions)
admin.site.register(Invoices)
admin.site.register(Payments)
admin.site.register(Staff)
admin.site.register(Users)
admin.site.register(ClinicSettings)
