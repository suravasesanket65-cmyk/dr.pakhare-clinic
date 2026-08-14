from django.db import models

class Patients(models.Model):
    PatientID = models.AutoField(primary_key=True)
    FirstName = models.CharField(max_length=50)
    LastName = models.CharField(max_length=50)
    Gender = models.CharField(max_length=10)
    DOB = models.DateField()
    Mobile = models.CharField(max_length=15)
    Email = models.EmailField(max_length=100)
    Address = models.TextField()
    BloodGroup = models.CharField(max_length=5, blank=True, null=True)
    Allergies = models.TextField(blank=True, null=True)
    MedicalHistory = models.TextField(blank=True, null=True)
    Photo = models.ImageField(upload_to='patients/', null=True, blank=True)
    RegistrationDate = models.DateField(auto_now_add=True)
    Status = models.CharField(max_length=20, default='Active')

    def __str__(self):
        return f"{self.FirstName} {self.LastName}"

class Doctors(models.Model):
    DoctorID = models.AutoField(primary_key=True)
    DoctorName = models.CharField(max_length=100)
    Qualification = models.CharField(max_length=100)
    Specialization = models.CharField(max_length=100)
    Experience = models.IntegerField()
    Mobile = models.CharField(max_length=15)
    Email = models.EmailField(max_length=100)
    AvailableDays = models.CharField(max_length=100)
    Status = models.CharField(max_length=20, default='Active')

    def __str__(self):
        return self.DoctorName

class Appointments(models.Model):
    AppointmentID = models.AutoField(primary_key=True)
    PatientID = models.ForeignKey(Patients, on_delete=models.CASCADE)
    DoctorID = models.ForeignKey(Doctors, on_delete=models.CASCADE)
    AppointmentDate = models.DateField()
    AppointmentTime = models.TimeField()
    Purpose = models.CharField(max_length=200)
    Status = models.CharField(max_length=20, default='Scheduled')
    CreatedDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appt {self.AppointmentID} - {self.PatientID}"

class Visits(models.Model):
    VisitID = models.AutoField(primary_key=True)
    AppointmentID = models.ForeignKey(Appointments, on_delete=models.CASCADE)
    VisitDate = models.DateField()
    Symptoms = models.TextField()
    Diagnosis = models.TextField()
    DoctorNotes = models.TextField()
    NextVisitDate = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Visit {self.VisitID}"

class Treatments(models.Model):
    TreatmentID = models.AutoField(primary_key=True)
    VisitID = models.ForeignKey(Visits, on_delete=models.CASCADE)
    TreatmentName = models.CharField(max_length=100)
    ToothNumber = models.CharField(max_length=20, blank=True, null=True)
    Procedure = models.TextField()
    TreatmentCost = models.DecimalField(max_digits=10, decimal_places=2)
    BeforeImage = models.ImageField(upload_to='treatments/', null=True, blank=True)
    AfterImage = models.ImageField(upload_to='treatments/', null=True, blank=True)
    Status = models.CharField(max_length=20, default='Completed')

    def __str__(self):
        return self.TreatmentName

class Prescriptions(models.Model):
    PrescriptionID = models.AutoField(primary_key=True)
    VisitID = models.ForeignKey(Visits, on_delete=models.CASCADE)
    MedicineName = models.CharField(max_length=100)
    Dosage = models.CharField(max_length=100)
    Frequency = models.CharField(max_length=50)
    Days = models.IntegerField()
    Instructions = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.MedicineName

class Invoices(models.Model):
    InvoiceID = models.AutoField(primary_key=True)
    VisitID = models.ForeignKey(Visits, on_delete=models.CASCADE)
    InvoiceDate = models.DateField(auto_now_add=True)
    TotalAmount = models.DecimalField(max_digits=10, decimal_places=2)
    Discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    GST = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    NetAmount = models.DecimalField(max_digits=10, decimal_places=2)
    Status = models.CharField(max_length=20, default='Unpaid')

    def __str__(self):
        return f"Invoice {self.InvoiceID}"

class Payments(models.Model):
    PaymentID = models.AutoField(primary_key=True)
    InvoiceID = models.ForeignKey(Invoices, on_delete=models.CASCADE)
    PaymentDate = models.DateField(auto_now_add=True)
    AmountPaid = models.DecimalField(max_digits=10, decimal_places=2)
    PaymentMode = models.CharField(max_length=20)
    TransactionID = models.CharField(max_length=100, blank=True, null=True)
    Remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment {self.PaymentID}"

class Staff(models.Model):
    StaffID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=100)
    Role = models.CharField(max_length=50)
    Mobile = models.CharField(max_length=15)
    Email = models.EmailField(max_length=100)
    JoiningDate = models.DateField()
    Salary = models.DecimalField(max_digits=10, decimal_places=2)
    Status = models.CharField(max_length=20, default='Active')

    def __str__(self):
        return self.Name

class Users(models.Model):
    UserID = models.AutoField(primary_key=True)
    Username = models.CharField(max_length=50, unique=True)
    Password = models.CharField(max_length=255)
    Role = models.CharField(max_length=20)
    LastLogin = models.DateTimeField(blank=True, null=True)
    Status = models.CharField(max_length=20, default='Active')

    def __str__(self):
        return self.Username

class ClinicSettings(models.Model):
    SettingID = models.AutoField(primary_key=True)
    ClinicName = models.CharField(max_length=100)
    Address = models.TextField()
    Phone = models.CharField(max_length=20)
    Email = models.EmailField(max_length=100)
    GSTNumber = models.CharField(max_length=30)
    WorkingHours = models.CharField(max_length=100)

    def __str__(self):
        return self.ClinicName

class AuditLogs(models.Model):
    LogID = models.AutoField(primary_key=True)
    Timestamp = models.DateTimeField(auto_now_add=True)
    Username = models.CharField(max_length=50)
    Role = models.CharField(max_length=20)
    Action = models.TextField()

    def __str__(self):
        return f"[{self.Timestamp}] {self.Username} ({self.Role}) - {self.Action}"

class WebsiteImage(models.Model):
    CATEGORY_CHOICES = [
        ('CLINIC', 'Clinic'),
        ('GALLERY', 'Gallery'),
    ]
    image = models.ImageField(upload_to='website_images/')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    def __str__(self):
        return f"{self.category} Image - {self.id}"

class ClinicProfile(models.Model):
    doctor_name = models.CharField(max_length=100, default='Dr. Pakhare')
    bio = models.TextField(default='Leading dental care specialist providing advanced treatments.')
    phone = models.CharField(max_length=20, default='+91 98765 43210')
    email = models.EmailField(max_length=100, default='info@drpakharedental.com')
    address = models.TextField(default='123 Healthcare Avenue, Medical District')
    working_hours = models.CharField(max_length=100, default='Mon - Sat: 9:00 AM - 8:30 PM')
    experience_years = models.CharField(max_length=50, default='Since 1990')
    instagram_link = models.URLField(max_length=200, blank=True, null=True, default='https://instagram.com')

    def __str__(self):
        return self.doctor_name

class PatientReview(models.Model):
    reviewer_name = models.CharField(max_length=100)
    reviewer_photo = models.ImageField(upload_to='reviews/profiles/', blank=True, null=True)
    treatment_photo = models.ImageField(upload_to='reviews/treatments/', blank=True, null=True)
    review_text = models.TextField()

    def __str__(self):
        return f"Review by {self.reviewer_name}"

