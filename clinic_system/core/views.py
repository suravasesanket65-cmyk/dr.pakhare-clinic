import csv
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Sum, Count
from datetime import date, datetime, timedelta, time
from core.models import Patients, Doctors, Appointments, Visits, Treatments, Prescriptions, Invoices, Payments, Users, ClinicSettings, Staff, AuditLogs, WebsiteImage, ClinicProfile, PatientReview

def log_action(request, action_description):
    try:
        username = request.session.get('username', 'System')
        role = request.session.get('role', 'Unknown')
        AuditLogs.objects.create(
            Username=username,
            Role=role,
            Action=action_description
        )
    except Exception:
        pass

def index(request):
    clinic_profile = ClinicProfile.objects.first()
    if not clinic_profile:
        clinic_profile = ClinicProfile.objects.create()
    website_images = WebsiteImage.objects.all()
    clinic_images = WebsiteImage.objects.filter(category='CLINIC')
    gallery_images = WebsiteImage.objects.filter(category='GALLERY')
    reviews = PatientReview.objects.all()
    context = {
        'clinic_profile': clinic_profile,
        'website_images': website_images,
        'clinic_images': clinic_images,
        'gallery_images': gallery_images,
        'reviews': reviews,
    }
    return render(request, 'core/index.html', context)

def clinic_dashboard(request):
    today = date.today()
    filter_param = request.GET.get('filter', 'today')
    
    today_appts_count = Appointments.objects.filter(AppointmentDate=today).count()
    total_patients = Patients.objects.count()
    
    total_revenue_agg = Invoices.objects.aggregate(total=Sum('NetAmount'))
    total_revenue = total_revenue_agg['total'] or 0
    
    pending_pay_count = Invoices.objects.filter(Status='Unpaid').count()
    
    current_month = today.month
    current_year = today.year
    monthly_income_agg = Payments.objects.filter(
        PaymentDate__year=current_year,
        PaymentDate__month=current_month
    ).aggregate(total=Sum('AmountPaid'))
    monthly_income = monthly_income_agg['total'] or 0
    
    active_doctors = Doctors.objects.filter(Status='Active')
    doc_performance = []
    for doc in active_doctors:
        count = Appointments.objects.filter(
            DoctorID=doc,
            AppointmentDate__year=current_year,
            AppointmentDate__month=current_month
        ).count()
        doc_performance.append({
            'doctor': doc,
            'count': count
        })
    
    if filter_param == 'tomorrow':
        tomorrow = today + timedelta(days=1)
        appointments = Appointments.objects.filter(AppointmentDate=tomorrow).order_by('AppointmentTime')
    elif filter_param == 'upcoming':
        appointments = Appointments.objects.filter(AppointmentDate__gt=today).order_by('AppointmentDate', 'AppointmentTime')
    elif filter_param == 'all':
        appointments = Appointments.objects.all().order_by('-AppointmentDate', 'AppointmentTime')
    else:
        appointments = Appointments.objects.filter(AppointmentDate=today).order_by('AppointmentTime')

    checked_in_appts = Appointments.objects.filter(
        Status__in=['Checked-In', 'In-Consultation', 'Treated', 'Billed']
    ).order_by('AppointmentDate', 'AppointmentTime')
    
    user_id = request.session.get('user_id')
    username = request.session.get('username', 'Doctor / Staff')
    if user_id:
        try:
            user_obj = Users.objects.get(UserID=user_id)
            username = user_obj.Username
        except Users.DoesNotExist:
            pass
    
    treatment_stats_qs = Treatments.objects.values('TreatmentName').annotate(count=Count('TreatmentID')).order_by('-count')[:5]
    total_treatments = Treatments.objects.count() or 1
    treatment_stats = []
    for ts in treatment_stats_qs:
        ts_dict = dict(ts)
        ts_dict['percentage'] = int((ts_dict['count'] / total_treatments) * 100)
        treatment_stats.append(ts_dict)
    
    context = {
        'today_appts_count': today_appts_count,
        'total_patients': total_patients,
        'total_revenue': total_revenue,
        'pending_pay_count': pending_pay_count,
        'monthly_income': monthly_income,
        'doc_performance': doc_performance,
        'treatment_stats': treatment_stats,
        'appointments': appointments,
        'today_appointments': appointments,
        'checked_in_appts': checked_in_appts,
        'current_filter': filter_param,
        'logged_in_username': username
    }
    return render(request, 'core/clinic_dashboard.html', context)

def check_in_patient(request, appointment_id):
    if request.session.get('role') == 'Patient':
        messages.error(request, 'Access Denied: Patients cannot access staff workflows.')
        return redirect('index')
    try:
        appt = Appointments.objects.get(AppointmentID=appointment_id)
        if appt.Status == 'Scheduled':
            Visits.objects.create(
                AppointmentID=appt,
                VisitDate=date.today(),
                Symptoms='',
                Diagnosis='',
                DoctorNotes=''
            )
            appt.Status = 'Checked-In'
            appt.save()
            log_action(request, f"Checked-in appointment ID #{appointment_id}")
            messages.success(request, f"{appt.PatientID.FirstName} successfully checked in!")
    except Appointments.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        
    return redirect('clinic_dashboard')

def get_or_create_visit_for_appointment(appointment_id):
    appt = Appointments.objects.get(AppointmentID=appointment_id)
    visit = Visits.objects.filter(AppointmentID=appt).first()
    if not visit:
        visit = Visits.objects.create(
            AppointmentID=appt,
            VisitDate=date.today(),
            Symptoms='Routine Consultation',
            Diagnosis='General Checkup',
            DoctorNotes=''
        )
    return visit

def consultation(request, appointment_id):
    if request.session.get('role') == 'Patient':
        messages.error(request, 'Access Denied: Patients cannot access clinical workflows.')
        return redirect('index')
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        
        if request.method == 'POST':
            visit.Symptoms = request.POST.get('Symptoms', '')
            visit.Diagnosis = request.POST.get('Diagnosis', '')
            visit.DoctorNotes = request.POST.get('DoctorNotes', '')
            visit.save()
            
            appt = visit.AppointmentID
            appt.Status = 'In-Consultation'
            appt.save()
            
            messages.success(request, 'Consultation notes saved!')
            return redirect('clinic_dashboard')
            
        context = {
            'visit': visit,
            'patient': patient
        }
        return render(request, 'core/consultation.html', context)
    except Visits.DoesNotExist:
        messages.error(request, 'Visit record not found. Patient must be checked in first.')
        return redirect('clinic_dashboard')

def patient_portal(request):
    if request.session.get('role') != 'Patient':
        return redirect('login')
    
    try:
        user_id = request.session.get('user_id')
        user = Users.objects.get(UserID=user_id)
        patient = Patients.objects.get(Email=user.Username)
        
        appointments = Appointments.objects.filter(PatientID=patient).order_by('-AppointmentDate')
        prescriptions = Prescriptions.objects.filter(VisitID__AppointmentID__PatientID=patient).order_by('-VisitID__VisitDate')
        invoices = Invoices.objects.filter(VisitID__AppointmentID__PatientID=patient).order_by('-InvoiceDate')
        
        context = {
            'patient': patient,
            'appointments': appointments,
            'prescriptions': prescriptions,
            'invoices': invoices,
        }
        return render(request, 'core/patient_portal.html', context)
        
    except (Users.DoesNotExist, Patients.DoesNotExist):
        request.session.flush()
        return redirect('login')

def logout_view(request):
    request.session.flush()
    return redirect('login')

def login_view(request):
    if request.method == 'POST':
        uname = request.POST.get('Username')
        pword = request.POST.get('Password')
        
        try:
            user = Users.objects.get(Username=uname)
            if check_password(pword, user.Password):
                request.session['user_id'] = user.UserID
                request.session['role'] = user.Role
                request.session['username'] = user.Username
                
                if user.Role in ['Doctor', 'Admin', 'Receptionist']:
                    return redirect('clinic_dashboard')
                elif user.Role == 'Patient':
                    return redirect('patient_portal')
                else:
                    return redirect('index')
            else:
                messages.error(request, 'Invalid Username or Password')
                return redirect('login')
        except Users.DoesNotExist:
            messages.error(request, 'Invalid Username or Password')
            return redirect('login')
            
    return render(request, 'core/login.html')

def patient_registration(request):
    if request.method == 'POST':
        email = request.POST.get('Email')
        password = request.POST.get('Password')
        
        Patients.objects.create(
            FirstName=request.POST.get('FirstName'),
            LastName=request.POST.get('LastName'),
            Gender=request.POST.get('Gender'),
            DOB=request.POST.get('DOB'),
            Mobile=request.POST.get('Mobile'),
            Email=email,
            Address=request.POST.get('Address'),
            BloodGroup=request.POST.get('BloodGroup'),
            Allergies=request.POST.get('Allergies'),
            MedicalHistory=request.POST.get('MedicalHistory'),
            Photo=request.FILES.get('Photo')
        )
        
        Users.objects.create(
            Username=email,
            Password=make_password(password),
            Role='Patient',
            Status='Active'
        )
        
        messages.success(request, 'Registration successful! Please login.')
        return redirect('login')
    return render(request, 'core/register.html')

def book_appointment(request):
    if request.method == 'POST':
        try:
            role = request.session.get('role')
            if role == 'Patient':
                user_id = request.session.get('user_id')
                user = Users.objects.get(UserID=user_id)
                patient = Patients.objects.get(Email=user.Username)
            else:
                patient_id = request.POST.get('PatientID')
                if not patient_id:
                    messages.error(request, 'Please provide a valid Patient ID.')
                    return redirect('book_appointment')
                patient = Patients.objects.get(PatientID=patient_id)
                
            doctor_id = request.POST.get('DoctorID')
            if not doctor_id:
                messages.error(request, 'Please select a Doctor for the appointment.')
                return redirect('book_appointment')
                
            try:
                doctor = Doctors.objects.get(DoctorID=doctor_id, Status='Active')
            except Doctors.DoesNotExist:
                doctor = Doctors.objects.filter(Status='Active').first()
                if not doctor:
                    messages.error(request, 'Selected doctor is not available. Please select another doctor.')
                    return redirect('book_appointment')
            
            Appointments.objects.create(
                PatientID=patient,
                DoctorID=doctor,
                AppointmentDate=request.POST.get('AppointmentDate'),
                AppointmentTime=request.POST.get('AppointmentTime'),
                Purpose=request.POST.get('Purpose'),
                Status='Scheduled'
            )
            
            messages.success(request, f'Appointment successfully scheduled with {doctor.DoctorName}!')
            if role == 'Patient':
                return redirect('patient_portal')
            else:
                return redirect('clinic_dashboard')
                
        except (Patients.DoesNotExist, Users.DoesNotExist, ValueError):
            messages.error(request, 'Error booking appointment: Patient record not found or invalid.')
            return redirect('book_appointment')
        except Exception as e:
            messages.error(request, f'Error booking appointment: {str(e)}')
            return redirect('book_appointment')
            
    doctors = Doctors.objects.filter(Status='Active')
    return render(request, 'core/book_appointment.html', {'doctors': doctors})

def treatment(request, appointment_id):
    if request.session.get('role') == 'Patient':
        messages.error(request, 'Access Denied: Patients cannot access clinical workflows.')
        return redirect('index')
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        
        if request.method == 'POST':
            Treatments.objects.create(
                VisitID=visit,
                TreatmentName=request.POST.get('TreatmentName'),
                ToothNumber=request.POST.get('ToothNumber', ''),
                Procedure=request.POST.get('Procedure'),
                TreatmentCost=request.POST.get('TreatmentCost'),
                BeforeImage=request.FILES.get('BeforeImage'),
                AfterImage=request.FILES.get('AfterImage')
            )
            appt = visit.AppointmentID
            appt.Status = 'Treated'
            appt.save()
            
            messages.success(request, 'Treatment logged successfully!')
            return redirect('clinic_dashboard')
            
        treatments = Treatments.objects.filter(VisitID__AppointmentID__PatientID=patient).order_by('-TreatmentID')
        context = {
            'visit': visit,
            'patient': patient,
            'treatments': treatments
        }
        return render(request, 'core/treatment.html', context)
    except Visits.DoesNotExist:
        messages.error(request, 'Visit record not found. Patient must be consulted first.')
        return redirect('clinic_dashboard')

def prescription(request, appointment_id):
    if request.session.get('role') == 'Patient':
        messages.error(request, 'Access Denied: Patients cannot access clinical workflows.')
        return redirect('index')
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        existing_prescriptions = Prescriptions.objects.filter(VisitID=visit)
        
        if request.method == 'POST':
            medicine_name = request.POST.get('MedicineName')
            if medicine_name:
                Prescriptions.objects.create(
                    VisitID=visit,
                    MedicineName=medicine_name,
                    Dosage=request.POST.get('Dosage', ''),
                    Frequency=request.POST.get('Frequency', ''),
                    Days=request.POST.get('Days', 0),
                    Instructions=request.POST.get('Instructions', '')
                )
            
            next_visit = request.POST.get('NextVisitDate')
            if next_visit:
                visit.NextVisitDate = next_visit
                visit.save()
                
            messages.success(request, 'Prescription added successfully.')
            return redirect('prescription', appointment_id=appointment_id)
            
        context = {
            'visit': visit,
            'patient': patient,
            'prescriptions': existing_prescriptions
        }
        return render(request, 'core/prescription.html', context)
    except Visits.DoesNotExist:
        messages.error(request, 'Visit record not found.')
        return redirect('clinic_dashboard')

def print_prescription(request, appointment_id):
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        prescriptions = Prescriptions.objects.filter(VisitID=visit)
        
        context = {
            'visit': visit,
            'patient': patient,
            'prescriptions': prescriptions,
            'today': date.today(),
            'clinic': ClinicSettings.objects.first()
        }
        return render(request, 'core/print_prescription.html', context)
    except Visits.DoesNotExist:
        messages.error(request, 'Visit record not found.')
        return redirect('clinic_dashboard')

def invoice(request, appointment_id):
    if request.session.get('role') == 'Patient':
        messages.error(request, 'Access Denied: Patients cannot access billing workflows.')
        return redirect('index')
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        treatments = Treatments.objects.filter(VisitID=visit)
        
        base_total = sum(t.TreatmentCost for t in treatments)
        
        if request.method == 'POST':
            total_amount = float(request.POST.get('TotalAmount', 0))
            discount = float(request.POST.get('Discount', 0))
            gst_percentage = float(request.POST.get('GST', 18))
            
            subtotal = total_amount - discount
            gst_amount = subtotal * (gst_percentage / 100.0)
            net_amount = subtotal + gst_amount
            
            Invoices.objects.create(
                VisitID=visit,
                TotalAmount=total_amount,
                Discount=discount,
                GST=gst_amount,
                NetAmount=net_amount,
                Status='Unpaid'
            )
            
            appt = visit.AppointmentID
            appt.Status = 'Billed'
            appt.save()
            
            messages.success(request, 'Invoice generated successfully.')
            return redirect('clinic_dashboard')
            
        context = {
            'visit': visit,
            'patient': patient,
            'treatments': treatments,
            'base_total': base_total
        }
        return render(request, 'core/invoice.html', context)
    except Visits.DoesNotExist:
        messages.error(request, 'Visit record not found.')
        return redirect('clinic_dashboard')

def payment(request, appointment_id):
    if request.session.get('role') == 'Patient':
        messages.error(request, 'Access Denied: Patients cannot access billing workflows.')
        return redirect('index')
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        invoice = Invoices.objects.get(VisitID=visit)
        payments = Payments.objects.filter(InvoiceID=invoice)
        
        amount_paid_so_far = sum(p.AmountPaid for p in payments)
        amount_due = float(invoice.NetAmount) - float(amount_paid_so_far)
        
        if request.method == 'POST':
            payment_amount = float(request.POST.get('AmountPaid', 0))
            
            if payment_amount > amount_due:
                messages.error(request, 'Error: Cannot overpay the invoice. Please check the amount.')
                return redirect('payment', appointment_id=appointment_id)
            
            Payments.objects.create(
                InvoiceID=invoice,
                AmountPaid=payment_amount,
                PaymentMode=request.POST.get('PaymentMode', ''),
                TransactionID=request.POST.get('TransactionID', ''),
                Remarks=request.POST.get('Remarks', '')
            )
            
            amount_paid_so_far += payment_amount
            new_amount_due = float(invoice.NetAmount) - float(amount_paid_so_far)
            
            if new_amount_due <= 0:
                invoice.Status = 'Paid'
                appt = visit.AppointmentID
                appt.Status = 'Completed'
                appt.save()
            else:
                invoice.Status = 'Partial'
            
            invoice.save()
            messages.success(request, 'Payment logged successfully.')
            return redirect('payment', appointment_id=appointment_id)
            
        context = {
            'visit': visit,
            'patient': patient,
            'invoice': invoice,
            'payments': payments,
            'amount_due': amount_due
        }
        return render(request, 'core/payment.html', context)
    except (Visits.DoesNotExist, Invoices.DoesNotExist):
        messages.error(request, 'Visit or Invoice record not found.')
        return redirect('clinic_dashboard')

def process_refund(request, payment_id):
    try:
        payment = Payments.objects.get(PaymentID=payment_id)
        invoice = payment.InvoiceID
        visit = invoice.VisitID
        
        if payment.AmountPaid <= 0:
            messages.error(request, 'Cannot refund an already refunded or negative amount.')
            return redirect('payment', appointment_id=visit.AppointmentID_id)
            
        Payments.objects.create(
            InvoiceID=invoice,
            AmountPaid=-payment.AmountPaid,
            PaymentMode='Refund',
            TransactionID=f"REFUND-{payment.PaymentID}",
            Remarks=f"Refund issued for Payment ID #{payment.PaymentID}"
        )
        
        all_payments = Payments.objects.filter(InvoiceID=invoice)
        total_paid = sum(p.AmountPaid for p in all_payments)
        
        if total_paid <= 0:
            invoice.Status = 'Unpaid'
        elif total_paid < invoice.NetAmount:
            invoice.Status = 'Partial'
        else:
            invoice.Status = 'Paid'
        invoice.save()
        
        if invoice.Status in ['Unpaid', 'Partial']:
            appt = visit.AppointmentID
            appt.Status = 'Billed'
            appt.save()
            
        log_action(request, f"Processed refund of ₹{payment.AmountPaid} for payment ID #{payment.PaymentID}")
        messages.success(request, f'Refund of ₹{payment.AmountPaid} processed successfully!')
        return redirect('payment', appointment_id=visit.AppointmentID_id)
    except Payments.DoesNotExist:
        messages.error(request, 'Payment record not found for refund.')
        return redirect('clinic_dashboard')
    except Exception as e:
        messages.error(request, f'Error processing refund: {str(e)}')
        return redirect('clinic_dashboard')

def print_receipt(request, appointment_id):
    try:
        visit = get_or_create_visit_for_appointment(appointment_id)
        patient = visit.AppointmentID.PatientID
        invoice = Invoices.objects.get(VisitID=visit)
        payments = Payments.objects.filter(InvoiceID=invoice)
        
        amount_paid_so_far = sum(p.AmountPaid for p in payments)
        amount_due = float(invoice.NetAmount) - float(amount_paid_so_far)
        
        context = {
            'visit': visit,
            'patient': patient,
            'invoice': invoice,
            'payments': payments,
            'amount_due': amount_due,
            'today': date.today(),
            'clinic': ClinicSettings.objects.first()
        }
        return render(request, 'core/print_receipt.html', context)
    except (Visits.DoesNotExist, Invoices.DoesNotExist):
        messages.error(request, 'Visit or Invoice record not found.')
        return redirect('clinic_dashboard')

def patient_list(request):
    patients = Patients.objects.all().order_by('-PatientID')
    return render(request, 'core/patient_list.html', {'patients': patients})

def appointment_list(request):
    appointments = Appointments.objects.all().order_by('-AppointmentDate', '-AppointmentTime')
    return render(request, 'core/appointment_list.html', {'appointments': appointments})

def cancel_appointment(request, appointment_id):
    try:
        appt = Appointments.objects.get(AppointmentID=appointment_id)
        appt.Status = 'Cancelled'
        appt.save()
        messages.success(request, f"Appointment #{appt.AppointmentID} for {appt.PatientID.FirstName} {appt.PatientID.LastName} has been cancelled.")
    except Appointments.DoesNotExist:
        messages.error(request, 'Appointment not found.')
    except Exception as e:
        messages.error(request, f"Error cancelling appointment: {str(e)}")
        
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('clinic_dashboard')

def reschedule_appointment(request, appointment_id):
    try:
        appt = Appointments.objects.get(AppointmentID=appointment_id)
        if request.method == 'POST':
            new_date = request.POST.get('AppointmentDate')
            new_time = request.POST.get('AppointmentTime')
            
            if not new_date or not new_time:
                messages.error(request, 'Please provide both a valid date and time.')
                return render(request, 'core/reschedule_appointment.html', {'appt': appt})
            
            conflict = Appointments.objects.filter(
                AppointmentDate=new_date,
                AppointmentTime=new_time
            ).exclude(Status='Cancelled').exclude(AppointmentID=appointment_id).exists()
            
            if conflict:
                messages.error(request, 'Selected date and time slot is already booked. Please choose another time.')
                return render(request, 'core/reschedule_appointment.html', {'appt': appt})
            
            appt.AppointmentDate = new_date
            appt.AppointmentTime = new_time
            appt.Status = 'Scheduled'
            appt.save()
            
            messages.success(request, f"Appointment #{appt.AppointmentID} successfully rescheduled to {new_date} at {new_time}!")
            
            role = request.session.get('role')
            if role == 'Patient':
                return redirect('patient_portal')
            return redirect('clinic_dashboard')
            
        return render(request, 'core/reschedule_appointment.html', {'appt': appt})
    except Appointments.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('clinic_dashboard')
    except Exception as e:
        messages.error(request, f"Error rescheduling appointment: {str(e)}")
        return redirect('clinic_dashboard')

def clinic_settings(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can manage clinic settings.')
        return redirect('clinic_dashboard')
        
    settings_obj = ClinicSettings.objects.first()
    if not settings_obj:
        settings_obj = ClinicSettings.objects.create(
            ClinicName="Dr. Pakhare Dental Clinic",
            Address="123 Dental Street, Healthcare City, MH 400001",
            Phone="+91 98765 43210",
            Email="contact@drpakharedental.com",
            GSTNumber="27AADCD1234F1Z9",
            WorkingHours="Mon - Sat: 09:00 AM - 08:00 PM"
        )
        
    if request.method == 'POST':
        settings_obj.ClinicName = request.POST.get('ClinicName', settings_obj.ClinicName)
        settings_obj.Address = request.POST.get('Address', settings_obj.Address)
        settings_obj.Phone = request.POST.get('Phone', settings_obj.Phone)
        settings_obj.Email = request.POST.get('Email', settings_obj.Email)
        settings_obj.GSTNumber = request.POST.get('GSTNumber', settings_obj.GSTNumber)
        settings_obj.WorkingHours = request.POST.get('WorkingHours', settings_obj.WorkingHours)
        settings_obj.save()
        log_action(request, "Updated clinic global configuration")
        messages.success(request, 'Clinic settings updated successfully!')
        return redirect('clinic_settings')
        
    return render(request, 'core/clinic_settings.html', {'settings': settings_obj})

def manage_cms(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can manage website CMS.')
        return redirect('clinic_dashboard')
        
    clinic_profile = ClinicProfile.objects.first()
    if not clinic_profile:
        clinic_profile = ClinicProfile.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            clinic_profile.doctor_name = request.POST.get('doctor_name', clinic_profile.doctor_name)
            clinic_profile.bio = request.POST.get('bio', clinic_profile.bio)
            clinic_profile.phone = request.POST.get('phone', clinic_profile.phone)
            clinic_profile.email = request.POST.get('email', clinic_profile.email)
            clinic_profile.address = request.POST.get('address', clinic_profile.address)
            clinic_profile.working_hours = request.POST.get('working_hours', clinic_profile.working_hours)
            clinic_profile.experience_years = request.POST.get('experience_years', clinic_profile.experience_years)
            clinic_profile.instagram_link = request.POST.get('instagram_link', clinic_profile.instagram_link)
            clinic_profile.save()
            log_action(request, "Updated Landing Page CMS Clinic Info")
            messages.success(request, 'Clinic Info updated successfully!')
        elif action == 'upload_image':
            image_file = request.FILES.get('image')
            category = request.POST.get('category', 'CLINIC')
            if image_file:
                WebsiteImage.objects.create(image=image_file, category=category)
                log_action(request, f"Uploaded CMS Image for category {category}")
                messages.success(request, 'Image uploaded successfully!')
            else:
                messages.error(request, 'Please select a valid image file.')
        elif action == 'delete_image':
            image_id = request.POST.get('image_id')
            try:
                img = WebsiteImage.objects.get(id=image_id)
                img.delete()
                log_action(request, f"Deleted CMS Image #{image_id}")
                messages.success(request, 'Image deleted successfully!')
            except WebsiteImage.DoesNotExist:
                messages.error(request, 'Image not found.')
        elif action == 'add_review':
            reviewer_name = request.POST.get('reviewer_name')
            review_text = request.POST.get('review_text')
            reviewer_photo = request.FILES.get('reviewer_photo')
            treatment_photo = request.FILES.get('treatment_photo')
            if reviewer_name and review_text:
                PatientReview.objects.create(
                    reviewer_name=reviewer_name,
                    review_text=review_text,
                    reviewer_photo=reviewer_photo,
                    treatment_photo=treatment_photo
                )
                log_action(request, f"Added Patient Review from {reviewer_name}")
                messages.success(request, 'Patient review added successfully!')
            else:
                messages.error(request, 'Reviewer name and review text are required.')
        elif action == 'delete_review':
            review_id = request.POST.get('review_id')
            try:
                rev = PatientReview.objects.get(id=review_id)
                rev.delete()
                log_action(request, f"Deleted Patient Review #{review_id}")
                messages.success(request, 'Patient review deleted successfully!')
            except PatientReview.DoesNotExist:
                messages.error(request, 'Review not found.')
        return redirect('manage_cms')

    website_images = WebsiteImage.objects.all().order_by('-id')
    reviews = PatientReview.objects.all().order_by('-id')
    context = {
        'clinic_profile': clinic_profile,
        'website_images': website_images,
        'reviews': reviews,
    }
    return render(request, 'core/manage_cms.html', context)

def staff_management(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can manage staff records.')
        return redirect('clinic_dashboard')
        
    if request.method == 'POST':
        try:
            Staff.objects.create(
                Name=request.POST.get('Name'),
                Role=request.POST.get('Role'),
                Mobile=request.POST.get('Mobile'),
                Email=request.POST.get('Email'),
                JoiningDate=request.POST.get('JoiningDate'),
                Salary=request.POST.get('Salary'),
                Status=request.POST.get('Status', 'Active')
            )
            log_action(request, f"Added new staff member: {request.POST.get('Name')}")
            messages.success(request, 'New staff member added successfully!')
        except Exception as e:
            messages.error(request, f"Error adding staff member: {str(e)}")
        return redirect('staff_management')
        
    staff_list = Staff.objects.all().order_by('-StaffID')
    return render(request, 'core/staff_management.html', {'staff_list': staff_list})

def doctor_management(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can manage doctor records.')
        return redirect('clinic_dashboard')
        
    if request.method == 'POST':
        try:
            Doctors.objects.create(
                DoctorName=request.POST.get('DoctorName'),
                Qualification=request.POST.get('Qualification'),
                Specialization=request.POST.get('Specialization'),
                Experience=request.POST.get('Experience'),
                Mobile=request.POST.get('Mobile'),
                Email=request.POST.get('Email'),
                AvailableDays=request.POST.get('AvailableDays'),
                Status=request.POST.get('Status', 'Active')
            )
            log_action(request, f"Registered new doctor: {request.POST.get('DoctorName')}")
            messages.success(request, 'New doctor registered successfully!')
        except Exception as e:
            messages.error(request, f"Error registering doctor: {str(e)}")
        return redirect('doctor_management')
        
    doctors_list = Doctors.objects.all().order_by('-DoctorID')
    return render(request, 'core/doctor_management.html', {'doctors_list': doctors_list})

def reports_center(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can access the Reports Center.')
        return redirect('clinic_dashboard')
    return render(request, 'core/reports_center.html')

def generate_csv_report(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can generate reports.')
        return redirect('clinic_dashboard')
        
    if request.method != 'POST':
        return redirect('reports_center')
        
    report_type = request.POST.get('report_type')
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Clinic_{report_type}_{date.today()}.csv"'
    writer = csv.writer(response)
    
    try:
        if report_type == 'Income Report':
            writer.writerow(['Payment ID', 'Invoice ID', 'Date', 'Mode', 'Transaction ID', 'Amount Paid', 'Remarks'])
            payments = Payments.objects.filter(PaymentDate__range=[start_date, end_date])
            for p in payments:
                writer.writerow([p.PaymentID, p.InvoiceID_id, p.PaymentDate, p.PaymentMode, p.TransactionID or '', p.AmountPaid, p.Remarks or ''])
        elif report_type == 'Patient Report':
            writer.writerow(['Patient ID', 'First Name', 'Last Name', 'Gender', 'DOB', 'Mobile', 'Email', 'Blood Group'])
            patients = Patients.objects.all()
            for p in patients:
                writer.writerow([p.PatientID, p.FirstName, p.LastName, p.Gender, p.DOB, p.Mobile, p.Email, p.BloodGroup])
        elif report_type == 'Appointment Report':
            writer.writerow(['Appointment ID', 'Patient', 'Doctor', 'Date', 'Time', 'Purpose', 'Status'])
            appointments = Appointments.objects.filter(AppointmentDate__range=[start_date, end_date])
            for a in appointments:
                writer.writerow([
                    a.AppointmentID,
                    f"{a.PatientID.FirstName} {a.PatientID.LastName}",
                    a.DoctorID.DoctorName if a.DoctorID else 'Unassigned',
                    a.AppointmentDate,
                    a.AppointmentTime,
                    a.Purpose,
                    a.Status
                ])
        elif report_type == 'Pending Fees':
            writer.writerow(['Invoice ID', 'Patient', 'Invoice Date', 'Total Amount', 'Discount', 'GST', 'Net Amount', 'Status'])
            invoices = Invoices.objects.filter(Status__in=['Unpaid', 'Partial'])
            for inv in invoices:
                patient_name = "N/A"
                try:
                    patient_name = f"{inv.VisitID.AppointmentID.PatientID.FirstName} {inv.VisitID.AppointmentID.PatientID.LastName}"
                except Exception:
                    pass
                writer.writerow([
                    inv.InvoiceID,
                    patient_name,
                    inv.InvoiceDate,
                    inv.TotalAmount,
                    inv.Discount,
                    inv.GST,
                    inv.NetAmount,
                    inv.Status
                ])
        elif report_type == 'Doctor Report':
            writer.writerow(['Doctor Name', 'Patient Name', 'Date', 'Time', 'Status'])
            appointments = Appointments.objects.filter(AppointmentDate__range=[start_date, end_date])
            for a in appointments:
                writer.writerow([
                    a.DoctorID.DoctorName if a.DoctorID else 'Unassigned',
                    f"{a.PatientID.FirstName} {a.PatientID.LastName}",
                    a.AppointmentDate,
                    a.AppointmentTime,
                    a.Status
                ])
        elif report_type == 'Treatment Report':
            writer.writerow(['Treatment Name', 'Tooth Number', 'Procedure', 'Cost', 'Status'])
            treatments = Treatments.objects.filter(VisitID__VisitDate__range=[start_date, end_date])
            for t in treatments:
                writer.writerow([
                    t.TreatmentName,
                    t.ToothNumber or 'N/A',
                    t.Procedure,
                    t.TreatmentCost,
                    t.Status
                ])
        else:
            writer.writerow(['Error: Unknown Report Type Selected'])
    except Exception as e:
        writer.writerow(['Error generating report', str(e)])
        
    return response

def backup_database(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can backup the database.')
        return redirect('clinic_dashboard')
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="DCMS_Master_Backup_{date.today()}.csv"'
    writer = csv.writer(response)
    
    try:
        writer.writerow(['=== MASTER PATIENT RECORDS ==='])
        writer.writerow(['PatientID', 'FirstName', 'LastName', 'Gender', 'DOB', 'Mobile', 'Email', 'Address', 'BloodGroup', 'Allergies', 'MedicalHistory'])
        for p in Patients.objects.all():
            writer.writerow([p.PatientID, p.FirstName, p.LastName, p.Gender, p.DOB, p.Mobile, p.Email, p.Address, p.BloodGroup, p.Allergies, p.MedicalHistory])
            
        writer.writerow([])
        writer.writerow(['=== MASTER APPOINTMENT RECORDS ==='])
        writer.writerow(['AppointmentID', 'PatientID', 'DoctorID', 'Date', 'Time', 'Purpose', 'Status'])
        for a in Appointments.objects.all():
            writer.writerow([a.AppointmentID, a.PatientID_id, a.DoctorID_id if a.DoctorID else '', a.AppointmentDate, a.AppointmentTime, a.Purpose, a.Status])
            
        writer.writerow([])
        writer.writerow(['=== MASTER PAYMENT RECORDS ==='])
        writer.writerow(['PaymentID', 'InvoiceID', 'Date', 'AmountPaid', 'Mode', 'TransactionID'])
        for pm in Payments.objects.all():
            writer.writerow([pm.PaymentID, pm.InvoiceID_id, pm.PaymentDate, pm.AmountPaid, pm.PaymentMode, pm.TransactionID])
            
    except Exception as e:
        writer.writerow(['Error creating backup', str(e)])
        
    return response

def audit_logs(request):
    if request.session.get('role') != 'Admin':
        messages.error(request, 'Access Denied: Only Admin can view audit logs.')
        return redirect('clinic_dashboard')
    logs = AuditLogs.objects.all().order_by('-Timestamp')
    return render(request, 'core/audit_logs.html', {'logs': logs})

def get_available_slots(request):
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'slots': []})
    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=400)

    start_time = datetime.strptime('09:00 AM', '%I:%M %p')
    end_time = datetime.strptime('08:00 PM', '%I:%M %p')

    appointments = Appointments.objects.filter(AppointmentDate=query_date).exclude(Status='Cancelled')
    booked_map = {}
    for appt in appointments:
        if appt.AppointmentTime:
            time_formatted = appt.AppointmentTime.strftime('%I:%M %p')
            booked_map[time_formatted] = appt
            booked_map[(appt.AppointmentTime.hour, appt.AppointmentTime.minute)] = appt

    user_role = str(request.session.get('role', '')).strip().lower()
    can_view_info = user_role in ['admin', 'receptionist', 'doctor', 'staff'] or (request.session.get('username') is not None and user_role != 'patient')

    slots = []
    current = start_time
    while current <= end_time:
        slot_str = current.strftime('%I:%M %p')
        time_key = (current.hour, current.minute)
        appt = booked_map.get(time_key) or booked_map.get(slot_str)
        is_booked = appt is not None

        doctor_name = None
        patient_info = None
        if is_booked:
            doctor_name = appt.DoctorID.DoctorName if appt.DoctorID else "Dr. Pakhare"
            if can_view_info:
                patient_name = f"{appt.PatientID.FirstName} {appt.PatientID.LastName}" if appt.PatientID else "Unknown Patient"
                purpose = appt.Purpose or "Appointment"
                patient_info = f"{patient_name} - {purpose}"

        slots.append({
            'time': slot_str,
            'is_booked': is_booked,
            'patient_info': patient_info,
            'doctor_name': doctor_name
        })
        current += timedelta(minutes=30)

    return JsonResponse({'slots': slots})

def master_schedule(request):
    if request.session.get('role') not in ['Admin', 'Doctor', 'Receptionist']:
        return redirect('login')
    return render(request, 'core/master_schedule.html')
