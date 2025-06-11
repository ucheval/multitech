from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django_otp.decorators import otp_required
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp import devices_for_user
from .models import Course, PaymentSlip, LiveSession, SessionRecap, Message, Cohort, CourseMaterial, AuditLog, Portfolio, Notification, Quiz, Question, Answer, QuizAttempt, Assignment, Project, Submission, DiscussionPost, DiscussionComment, PerformanceRecord, SalarySubmission, FacilitatorApplication, Profile, CourseEnrollment, SessionAttendance, OnboardingQuizResponse, PaymentDetail
from .forms import PaymentSlipForm, PortfolioForm, CustomRegistrationForm, OnboardingQuizForm, FacilitatorProfileForm, CourseChangeForm, CourseForm
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.utils.html import escape
import qrcode
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from io import BytesIO
import base64
from django.http import JsonResponse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
import logging
from phonenumbers import parse, is_valid_number, NumberParseException
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

def register(request):
    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different one.')
                return render(request, 'core/register.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})
            
            user = form.save()
            user.email = form.cleaned_data['email']
            user.save()
            logger.info(f"User {user.username} registered successfully with user_type: {form.cleaned_data['user_type']}, course: {form.cleaned_data['course'].title if form.cleaned_data['course'] else 'None'}")
            
            if Profile.objects.filter(user=user).exists():
                messages.error(request, 'A profile already exists for this user. Please contact support.')
                return render(request, 'core/register.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})
            
            try:
                profile = Profile.objects.create(
                    user=user,
                    user_type=form.cleaned_data['user_type'],
                    profile_picture=form.cleaned_data['profile_picture'],
                    mobile_number=form.cleaned_data.get('mobile_number', ''),
                    country=form.cleaned_data['country'],
                    onboarding_quiz_completed=False if form.cleaned_data['user_type'] == 'student' else True,
                    facilitator_profile_completed=False if form.cleaned_data['user_type'] == 'facilitator' else True
                )
                logger.info(f"Generated passcode {profile.student_passcode} for student {user.username}")
            except Exception as e:
                logger.error(f"Failed to create profile for {user.username}: {str(e)}")
                user.delete()
                messages.error(request, 'An error occurred during registration. Please try again or contact support.')
                return render(request, 'core/register.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})
            
            course = form.cleaned_data['course']
            if form.cleaned_data['user_type'] == 'facilitator' and course:
                FacilitatorApplication.objects.create(
                    user=user,
                    course=course,
                    status='pending'
                )
                logger.info(f"FacilitatorApplication created for {user.username} for course {course.title}")
                Notification.objects.create(
                    user=user,
                    type='courses',
                    message=f'Your application to facilitate {course.title} has been submitted and is pending admin approval.'
                )
            elif form.cleaned_data['user_type'] == 'student' and course:
                front_end_keywords = ['HTML', 'CSS', 'JavaScript', 'React', 'Frontend', 'Front-end', 'Web Development', 'UI', 'UX']
                back_end_keywords = ['Python', 'Django', 'Node', 'Backend', 'Back-end', 'Database', 'API']
                course_title_lower = course.title.lower()
                if any(keyword.lower() in course_title_lower for keyword in front_end_keywords):
                    cohort_type = 'Front-end'
                elif any(keyword.lower() in course_title_lower for keyword in back_end_keywords):
                    cohort_type = 'Back-end'
                else:
                    cohort_type = 'General'
                logger.info(f"Course {course.title} assigned cohort type: {cohort_type}")
                
                latest_cohort = Cohort.objects.filter(
                    course=course,
                    name__startswith=f"{cohort_type} Cohort"
                ).order_by('-name').first()
                
                if not latest_cohort or latest_cohort.students.count() >= 15:
                    if latest_cohort:
                        try:
                            last_number = int(latest_cohort.name.split()[-1])
                            new_number = last_number + 1
                        except ValueError:
                            new_number = 1
                    else:
                        new_number = 1
                    cohort_name = f"{cohort_type} Cohort {new_number:02d}"
                    latest_cohort = Cohort.objects.create(
                        course=course,
                        name=cohort_name,
                        whatsapp_link=f"https://chat.whatsapp.com/{cohort_name.replace(' ', '_')}_placeholder"
                    )
                    logger.info(f"Created new cohort {cohort_name} for course {course.title} with placeholder WhatsApp link")
                
                enrollment = CourseEnrollment.objects.create(
                    user=user,
                    course=course,
                    status='pending'
                )
                latest_cohort.students.add(user)
                logger.info(f"Assigned {user.username} to cohort {latest_cohort.name} for course {course.title}")
                
                Notification.objects.create(
                    user=user,
                    type='courses',
                    message=f'Your enrollment request for {course.title} is pending approval. You have been assigned to {latest_cohort.name}.'
                )
                send_mail(
                    'Enrollment Request',
                    f'Your enrollment request for {course.title} is pending approval. You have been assigned to {latest_cohort.name}. Join the WhatsApp group: {latest_cohort.whatsapp_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            login(request, user)
            messages.success(request, 'Registration successful.')
            AuditLog.objects.create(
                user=user,
                action='User Registered',
                details=f"User {user.username} registered as {form.cleaned_data['user_type']} with course {course.title if course else 'None'}"
            )
            if user.is_superuser:
                logger.info(f"Redirecting superuser {user.username} to admindashboard")
                return redirect('admindashboard')
            elif profile.user_type == 'facilitator':
                logger.info(f"Redirecting facilitator {user.username} to facilitator_application")
                return redirect('facilitator_application')
            else:
                logger.info(f"Redirecting student {user.username} to onboarding_quiz")
                return redirect('onboarding_quiz')
        else:
            logger.warning(f"Registration failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors.as_json()})
    else:
        form = CustomRegistrationForm()
    return render(request, 'core/register.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})

def user_login(request):
    next_url = request.GET.get('next', None)
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            if request.user.is_superuser:
                logger.info(f"Superuser {request.user.username} is authenticated")
                return redirect(next_url) if next_url else redirect('admindashboard')
            if profile.user_type == 'student' and not profile.onboarding_quiz_completed:
                logger.info(f"Redirecting student {request.user.username} to onboarding_quiz")
                return redirect('onboarding_quiz')
            return redirect(next_url) if next_url else redirect('student_dashboard')
        except Profile.DoesNotExist:
            logger.warning(f"User {request.user.username} has no profile, redirecting to create_profile")
            return redirect('create_profile')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful.')
                AuditLog.objects.create(
                    user=user,
                    action='login',
                    details='User logged in successfully'
                )
                try:
                    profile = user.profile
                    if user.is_superuser:
                        logger.info(f"Redirecting superuser {user.username} to next_url or admindashboard")
                        return redirect(next_url) if next_url else redirect('admindashboard')
                    if profile.user_type == 'student' and not profile.onboarding_quiz_completed:
                        logger.info(f"Redirecting student {user.username} to onboarding_quiz")
                        return redirect('onboarding_quiz')
                    return redirect(next_url) if next_url else redirect('student_dashboard')
                except Profile.DoesNotExist:
                    logger.warning(f"User {user.username} has no profile, redirecting to create_profile")
                    return redirect('create_profile')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})
def create_profile(request):
    if not request.user.is_authenticated:
        return redirect('user_login')
    
    if hasattr(request.user, 'profile'):
        logger.info(f"User {request.user.username} already has a profile, redirecting to student_dashboard")
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                profile = Profile.objects.create(
                    user=request.user,
                    user_type=form.cleaned_data['user_type'],
                    profile_picture=form.cleaned_data['profile_picture'],
                    mobile_number=form.cleaned_data.get('mobile_number', ''),
                    country=form.cleaned_data['country'],
                    onboarding_quiz_completed=False if form.cleaned_data['user_type'] == 'student' else True,
                    facilitator_profile_completed=False if form.cleaned_data['user_type'] == 'facilitator' else True
                )
                logger.info(f"Created profile for {request.user.username} with passcode {profile.student_passcode}")
                messages.success(request, 'Profile created successfully.')
                AuditLog.objects.create(
                    user=request.user,
                    action='Profile Created',
                    details=f"User {request.user.username} created profile as {form.cleaned_data['user_type']}"
                )
                if form.cleaned_data['user_type'] == 'student' and not form.cleaned_data['course']:
                    return redirect('onboarding_quiz')
                return redirect('student_dashboard')
            except Exception as e:
                logger.error(f"Failed to create profile for {request.user.username}: {str(e)}")
                messages.error(request, 'An error occurred. Please try again or contact support.')
        else:
            logger.warning(f"Profile creation failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomRegistrationForm()
    return render(request, 'core/create_profile.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})

    if request.user.is_authenticated:
        return redirect('student_dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successful.')
                AuditLog.objects.create(
                    user=user,
                    action='login',
                    details='User logged in successfully'
                )
                if user.profile.user_type == 'student' and not user.profile.onboarding_quiz_completed:
                    return redirect('onboarding_quiz')
                return redirect('student_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})
def user_logout(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('landing')
from django.urls import reverse

def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    enrolled = CourseEnrollment.objects.filter(user=request.user, course=course).exists() if request.user.is_authenticated else False
    return render(request, 'core/course_detail.html', {'course': course, 'enrolled': enrolled, 'logo_base64': settings.LOGO_BASE64})

@login_required
def course_enrollment(request):
    if request.user.profile.user_type != 'student':
        messages.error(request, 'Only students can access course enrollment.')
        return redirect('student_dashboard')
    
    enrollment = CourseEnrollment.objects.filter(user=request.user).first()
    payment_slip = PaymentSlip.objects.filter(user=request.user, course=enrollment.course).first() if enrollment else None
    payment_detail = PaymentDetail.objects.first() or PaymentDetail.objects.create()  # Get or create payment details
    payment_details = {
        'bank': {
            'name': payment_detail.bank_name,
            'account_number': payment_detail.bank_account_number,
            'account_name': payment_detail.bank_account_name,
        },
        'momo': {
            'name': payment_detail.momo_name,
            'number': payment_detail.momo_number,
            'provider': payment_detail.momo_provider,
        }
    }

    if enrollment and enrollment.status == 'approved':
        messages.info(request, 'You are already enrolled in a course.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        if not enrollment:
            messages.error(request, 'No course selected. Please register with a course or change your course.')
            return redirect('change_course')
        return redirect('upload_payment_slip', course_id=enrollment.course.id)
    
    return render(request, 'core/course_enrollment.html', {
        'enrollment': enrollment,
        'payment_slip': payment_slip,
        'payment_details': payment_details,
        'logo_base64': settings.LOGO_BASE64
    })
@login_required
def change_course(request):
    if request.user.profile.user_type != 'student':
        messages.error(request, 'Only students can change courses.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        form = CourseChangeForm(request.POST)
        if form.is_valid():
            new_course = form.cleaned_data['course']
            existing_enrollment = CourseEnrollment.objects.filter(user=request.user, status__in=['pending', 'approved']).first()
            if existing_enrollment:
                old_course = existing_enrollment.course
                existing_enrollment.course = new_course
                existing_enrollment.status = 'pending'
                existing_enrollment.save()
                logger.info(f"Updated CourseEnrollment for {request.user.username} from {old_course.title} to {new_course.title}")
                message = f'Your request to change from {old_course.title} to {new_course.title} is pending approval.'
            else:
                CourseEnrollment.objects.create(
                    user=request.user,
                    course=new_course,
                    status='pending'
                )
                logger.info(f"Created new CourseEnrollment for {request.user.username} for course {new_course.title}")
                message = f'Your enrollment request for {new_course.title} is pending approval.'
            
            Notification.objects.create(
                user=request.user,
                type='general',
                message=message
            )
            send_mail(
                'Course Change Request',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=True,
            )
            messages.success(request, 'Course change request submitted successfully.')
            AuditLog.objects.create(
                user=request.user,
                action='Course Change Requested',
                details=f"User {request.user.username} requested to change to course {new_course.title}"
            )
            return redirect('student_dashboard')
        else:
            logger.warning(f"Course change failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseChangeForm()
    return render(request, 'core/change_course.html', {'form': form, 'logo_base64': settings.LOGO_BASE64})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_facilitators(request):
    applications = FacilitatorApplication.objects.all()
    if request.method == 'POST':
        app_id = request.POST.get('app_id')
        action = request.POST.get('action')
        application = get_object_or_404(FacilitatorApplication, id=app_id)
        if action == 'approve':
            application.status = 'approved'
            application.user.is_staff = True
            if not Course.objects.filter(facilitator=application.user, id=application.course.id).exists():
                application.course.facilitator = application.user
                application.course.save()
            application.user.save()
            Portfolio.objects.get_or_create(
                user=application.user,
                defaults={
                    'name': application.user.username,
                    'bio': '',
                    'github_url': '',
                    'skills': '',
                    'projects': '',
                    'certificates': '',
                    'is_public': False
                }
            )
            Notification.objects.create(
                user=application.user,
                type='general',
                message=f'You have been approved as facilitator for {application.course.title}.'
            )
            Message.objects.create(
                sender=request.user,
                recipient=application.user,
                content=f'Congratulations! Your application to facilitate {application.course.title} has been approved. You can now view students, create classes, and manage cohorts.'
            )
            AuditLog.objects.create(
                user=request.user,
                action='Facilitator Approved',
                details=f"Approved {application.user.username} for {application.course.title}"
            )
        elif action == 'reject':
            application.status = 'rejected'
            Notification.objects.create(
                user=application.user,
                type='general',
                message=f'Your facilitator application for {application.course.title} was rejected.'
            )
            Message.objects.create(
                sender=request.user,
                recipient=application.user,
                content=f'Sorry, your application to facilitate {application.course.title} was rejected. Please contact the admin for more details or apply for another course.'
            )
            AuditLog.objects.create(
                user=request.user,
                action='Facilitator Rejected',
                details=f"Rejected {application.user.username} for {application.course.title}"
            )
        application.save()
        messages.success(request, f'Application {action}d.')
        return redirect('manage_facilitators')
    return render(request, 'core/manage_facilitators.html', {'applications': applications, 'logo_base64': settings.LOGO_BASE64})

def course_list(request):
    courses = Course.objects.all()
    enrolled_course_ids = []
    if request.user.is_authenticated:
        enrolled_course_ids = CourseEnrollment.objects.filter(user=request.user).values_list('course_id', flat=True)
    return render(request, 'core/course_list.html', {'courses': courses, 'enrolled_course_ids': enrolled_course_ids, 'logo_base64': settings.LOGO_BASE64})

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_approved_facilitator = FacilitatorApplication.objects.filter(
        user=request.user,
        course=course,
        status='approved'
    ).exists()
    
    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={'status': 'approved' if is_approved_facilitator else 'pending'}
    )
    if created:
        front_end_keywords = ['HTML', 'CSS', 'JavaScript', 'React', 'Frontend', 'Front-end', 'Web Development', 'UI', 'UX']
        back_end_keywords = ['Python', 'Django', 'Node', 'Backend', 'Back-end', 'Database', 'API']
        course_title_lower = course.title.lower()
        if any(keyword.lower() in course_title_lower for keyword in front_end_keywords):
            cohort_type = 'Front-end'
        elif any(keyword.lower() in course_title_lower for keyword in back_end_keywords):
            cohort_type = 'Back-end'
        else:
            cohort_type = 'General'
        logger.info(f"Course {course.title} assigned cohort type: {cohort_type}")
        
        latest_cohort = Cohort.objects.filter(
            course=course,
            name__startswith=f"{cohort_type} Cohort"
        ).order_by('-name').first()
        
        if not latest_cohort or latest_cohort.students.count() >= 15:
            if latest_cohort:
                try:
                    last_number = int(latest_cohort.name.split()[-1])
                    new_number = last_number + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1
            cohort_name = f"{cohort_type} Cohort {new_number:02d}"
            latest_cohort = Cohort.objects.create(
                course=course,
                name=cohort_name,
                whatsapp_link=f"https://chat.whatsapp.com/{cohort_name.replace(' ', '_')}_placeholder"
            )
            logger.info(f"Created new cohort {cohort_name} for course {course.title} with placeholder WhatsApp link")
        
        latest_cohort.students.add(request.user)
        logger.info(f"Assigned {request.user.username} to cohort {latest_cohort.name} for course {course.title}")
        
        if is_approved_facilitator:
            messages.success(request, f'You are enrolled in {course.title} as a facilitator (no payment required).')
        else:
            messages.success(request, f'Enrollment request for {course.title} submitted. You have been assigned to {latest_cohort.name}. Please upload your payment slip.')
            send_mail(
                'Enrollment Request',
                f'Your enrollment request for {course.title} is pending approval. You have been assigned to {latest_cohort.name}. Join the WhatsApp group: {latest_cohort.whatsapp_link}',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=True,
            )
    else:
        messages.info(request, f'You are already enrolled or have a pending request for {course.title}.')
    return redirect('course_enrollment')

@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
# @otp_required
def manage_cohorts(request):
    cohorts = Cohort.objects.all().select_related('course').prefetch_related('students').order_by('name')
    
    if request.method == 'POST':
        cohort_id = request.POST.get('cohort_id')
        action = request.POST.get('action')
        cohort = get_object_or_404(Cohort, id=cohort_id)
        
        if action == 'approve':
            approved_students = User.objects.filter(
                courseenrollment__course=cohort.course,
                courseenrollment__status='approved'
            ).exclude(cohorts=cohort)
            cohort.students.add(*approved_students)
            logger.info(f"Approved cohort {cohort.name} with {approved_students.count()} students added")
            messages.success(request, f'Cohort {cohort.name} approved with {approved_students.count()} students added.')
            AuditLog.objects.create(
                user=request.user,
                action='Cohort Approved',
                details=f"Approved cohort {cohort.name} with {approved_students.count()} students"
            )
        elif action == 'delete':
            cohort_name = cohort.name
            cohort.delete()
            logger.info(f"Deleted cohort {cohort_name}")
            messages.success(request, f'Cohort {cohort_name} deleted.')
            AuditLog.objects.create(
                user=request.user,
                action='Cohort Deleted',
                details=f"Deleted cohort {cohort_name}"
            )
        elif action == 'update_whatsapp':
            whatsapp_link = request.POST.get('whatsapp_link', '').strip()
            if whatsapp_link:
                validate = URLValidator()
                try:
                    validate(whatsapp_link)
                    if not whatsapp_link.startswith('https://chat.whatsapp.com/'):
                        raise ValidationError('Invalid WhatsApp group link.')
                    cohort.whatsapp_link = whatsapp_link
                    cohort.save()
                    logger.info(f"Updated WhatsApp link for cohort {cohort.name}")
                    messages.success(request, f'WhatsApp link for {cohort.name} updated.')
                    AuditLog.objects.create(
                        user=request.user,
                        action='WhatsApp Link Updated',
                        details=f"Updated WhatsApp link for cohort {cohort.name}"
                    )
                except ValidationError:
                    logger.warning(f"Invalid WhatsApp link for cohort {cohort.name}: {whatsapp_link}")
                    messages.error(request, 'Please provide a valid WhatsApp group link (e.g., https://chat.whatsapp.com/ABC123).')
            else:
                cohort.whatsapp_link = ''
                cohort.save()
                logger.info(f"Cleared WhatsApp link for cohort {cohort.name}")
                messages.success(request, f'WhatsApp link for {cohort.name} cleared.')
                AuditLog.objects.create(
                    user=request.user,
                    action='WhatsApp Link Cleared',
                    details=f"Cleared WhatsApp link for cohort {cohort.name}"
                )
        
        return redirect('manage_cohorts')
    
    cohort_data = [
        {
            'id': cohort.id,
            'name': cohort.name,
            'course_title': cohort.course.title,
            'students': [
                {'username': student.username, 'full_name': f"{student.first_name} {student.last_name}".strip()}
                for student in cohort.students.all()
            ],
            'student_count': cohort.students.count(),
            'whatsapp_link': cohort.whatsapp_link or '',
            'student_leader': cohort.student_leader.username if cohort.student_leader else 'None',
        }
        for cohort in cohorts
    ]
    
    return render(request, 'core/manage_cohorts.html', {
        'cohorts': cohort_data,
        'logo_base64': settings.LOGO_BASE64
    })
    cohorts = Cohort.objects.all().select_related('course').prefetch_related('students').order_by('name')
    
    if request.method == 'POST':
        cohort_id = request.POST.get('cohort_id')
        action = request.POST.get('action')
        cohort = get_object_or_404(Cohort, id=cohort_id)
        
        if action == 'approve':
            approved_students = User.objects.filter(
                courseenrollment__course=cohort.course,
                courseenrollment__status='approved'
            ).exclude(cohorts=cohort)
            cohort.students.add(*approved_students)
            logger.info(f"Approved cohort {cohort.name} with {approved_students.count()} students added")
            messages.success(request, f'Cohort {cohort.name} approved with {approved_students.count()} students added.')
            AuditLog.objects.create(
                user=request.user,
                action='Cohort Approved',
                details=f"Approved cohort {cohort.name} with {approved_students.count()} students"
            )
        elif action == 'delete':
            cohort_name = cohort.name
            cohort.delete()
            logger.info(f"Deleted cohort {cohort_name}")
            messages.success(request, f'Cohort {cohort_name} deleted.')
            AuditLog.objects.create(
                user=request.user,
                action='Cohort Deleted',
                details=f"Deleted cohort {cohort_name}"
            )
        elif action == 'update_whatsapp':
            whatsapp_link = request.POST.get('whatsapp_link', '').strip()
            if whatsapp_link:
                validate = URLValidator()
                try:
                    validate(whatsapp_link)
                    if not whatsapp_link.startswith('https://chat.whatsapp.com/'):
                        raise ValidationError('Invalid WhatsApp group link.')
                    cohort.whatsapp_link = whatsapp_link
                    cohort.save()
                    logger.info(f"Updated WhatsApp link for cohort {cohort.name}")
                    messages.success(request, f'WhatsApp link for {cohort.name} updated.')
                    AuditLog.objects.create(
                        user=request.user,
                        action='WhatsApp Link Updated',
                        details=f"Updated WhatsApp link for cohort {cohort.name}"
                    )
                except ValidationError:
                    logger.warning(f"Invalid WhatsApp link for cohort {cohort.name}: {whatsapp_link}")
                    messages.error(request, 'Please provide a valid WhatsApp group link (e.g., https://chat.whatsapp.com/ABC123).')
            else:
                cohort.whatsapp_link = ''
                cohort.save()
                logger.info(f"Cleared WhatsApp link for cohort {cohort.name}")
                messages.success(request, f'WhatsApp link for {cohort.name} cleared.')
                AuditLog.objects.create(
                    user=request.user,
                    action='WhatsApp Link Cleared',
                    details=f"Cleared WhatsApp link for cohort {cohort.name}"
                )
        
        return redirect('manage_cohorts')
    
    cohort_data = [
        {
            'id': cohort.id,
            'name': cohort.name,
            'course_title': cohort.course.title,
            'students': [
                {'username': student.username, 'full_name': f"{student.first_name} {student.last_name}".strip()}
                for student in cohort.students.all()
            ],
            'student_count': cohort.students.count(),
            'whatsapp_link': cohort.whatsapp_link or '',
            'student_leader': cohort.student_leader.username if cohort.student_leader else 'None',
        }
        for cohort in cohorts
    ]
    
    return render(request, 'core/manage_cohorts.html', {
        'cohorts': cohort_data,
        'logo_base64': settings.LOGO_BASE64
    })
    cohorts = Cohort.objects.all().select_related('course').prefetch_related('students').order_by('name')
    
    if request.method == 'POST':
        cohort_id = request.POST.get('cohort_id')
        action = request.POST.get('action')
        cohort = get_object_or_404(Cohort, id=cohort_id)
        
        if action == 'approve':
            approved_students = User.objects.filter(
                courseenrollment__course=cohort.course,
                courseenrollment__status='approved'
            ).exclude(cohorts=cohort)
            cohort.students.add(*approved_students)
            logger.info(f"Approved cohort {cohort.name} with {approved_students.count()} students added")
            messages.success(request, f'Cohort {cohort.name} approved with {approved_students.count()} students added.')
            AuditLog.objects.create(
                user=request.user,
                action='Cohort Approved',
                details=f"Approved cohort {cohort.name} with {approved_students.count()} students"
            )
        elif action == 'delete':
            cohort_name = cohort.name
            cohort.delete()
            logger.info(f"Deleted cohort {cohort_name}")
            messages.success(request, f'Cohort {cohort_name} deleted.')
            AuditLog.objects.create(
                user=request.user,
                action='Cohort Deleted',
                details=f"Deleted cohort {cohort_name}"
            )
        elif action == 'update_whatsapp':
            whatsapp_link = request.POST.get('whatsapp_link', '').strip()
            if whatsapp_link:
                validate = URLValidator()
                try:
                    validate(whatsapp_link)
                    if not whatsapp_link.startswith('https://chat.whatsapp.com/'):
                        raise ValidationError('Invalid WhatsApp group link.')
                    cohort.whatsapp_link = whatsapp_link
                    cohort.save()
                    logger.info(f"Updated WhatsApp link for cohort {cohort.name}")
                    messages.success(request, f'WhatsApp link for {cohort.name} updated.')
                    AuditLog.objects.create(
                        user=request.user,
                        action='WhatsApp Link Updated',
                        details=f"Updated WhatsApp link for cohort {cohort.name}"
                    )
                except ValidationError:
                    logger.warning(f"Invalid WhatsApp link for cohort {cohort.name}: {whatsapp_link}")
                    messages.error(request, 'Please provide a valid WhatsApp group link (e.g., https://chat.whatsapp.com/ABC123).')
            else:
                cohort.whatsapp_link = ''
                cohort.save()
                logger.info(f"Cleared WhatsApp link for cohort {cohort.name}")
                messages.success(request, f'WhatsApp link for {cohort.name} cleared.')
                AuditLog.objects.create(
                    user=request.user,
                    action='WhatsApp Link Cleared',
                    details=f"Cleared WhatsApp link for cohort {cohort.name}"
                )
        
        return redirect('manage_cohorts')
    
    cohort_data = [
        {
            'id': cohort.id,
            'name': cohort.name,
            'course_title': cohort.course.title,
            'students': [
                {'username': student.username, 'full_name': f"{student.first_name} {student.last_name}".strip()}
                for student in cohort.students.all()
            ],
            'student_count': cohort.students.count(),
            'whatsapp_link': cohort.whatsapp_link or '',
        }
        for cohort in cohorts
    ]
    
    return render(request, 'core/manage_cohorts.html', {
        'cohorts': cohort_data,
        'logo_base64': settings.LOGO_BASE64
    })
@login_required
@user_passes_test(lambda u: u.is_staff or u.profile.user_type == 'facilitator')
def schedule_session(request):
    if request.method == 'POST':
        course_id = request.POST.get('course')
        title = request.POST.get('title')
        zoom_url = request.POST.get('zoom_url')
        scheduled_at = request.POST.get('scheduled_at')
        end_time = request.POST.get('end_time')
        session_type = request.POST.get('session_type')
        is_open_to_all = request.POST.get('is_open_to_all') == 'on'

        if not all([course_id, title, zoom_url, scheduled_at, end_time]):
            messages.error(request, 'All required fields must be filled.')
            return redirect('schedule_session')

        try:
            scheduled_at = timezone.datetime.strptime(scheduled_at, '%Y-%m-%dT%H:%M')
            end_time = timezone.datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
            scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
            end_time = timezone.make_aware(end_time, timezone.get_current_timezone())

            if scheduled_at < timezone.now():
                messages.error(request, 'Scheduled time must be in the future.')
                return redirect('schedule_session')
            if end_time <= scheduled_at:
                messages.error(request, 'End time must be after scheduled time.')
                return redirect('schedule_session')
            URLValidator()(zoom_url)
        except (ValueError, ValidationError) as e:
            messages.error(request, f'Invalid input: {str(e)}')
            return redirect('schedule_session')

        course = get_object_or_404(Course, id=course_id)
        if request.user.profile.user_type == 'facilitator' and course.facilitator != request.user:
            messages.error(request, 'You can only schedule sessions for courses you facilitate.')
            return redirect('schedule_session')

        session = LiveSession.objects.create(
            course=course,
            title=title,
            zoom_url=zoom_url,
            scheduled_at=scheduled_at,
            end_time=end_time,
            created_by=request.user,
            session_type=session_type,
            is_visible=True,
            is_open_to_all=is_open_to_all
        )

        # Notify students
        if is_open_to_all:
            recipients = User.objects.filter(profile__user_type='student').values_list('id', flat=True)
        else:
            recipients = CourseEnrollment.objects.filter(
                course=course, status='approved'
            ).values_list('user_id', flat=True)

        notifications = [
            Notification(
                user_id=user_id,
                type='general',
                message=f"New live session '{session.title}' scheduled for {session.scheduled_at}. Join at: {session.zoom_url}"
            )
            for user_id in recipients
        ]
        Notification.objects.bulk_create(notifications)

        messages.success(request, f'Session {title} scheduled.')
        AuditLog.objects.create(
            user=request.user,
            action='Session Scheduled',
            details=f"Scheduled session {session.title} for course {course.title}"
        )
        return redirect('live_session')

    courses = Course.objects.filter(facilitator=request.user) if request.user.profile.user_type == 'facilitator' else Course.objects.all()
    return render(request, 'core/schedule_session.html', {
        'courses': courses,
        'logo_base64': settings.LOGO_BASE64
    })

@login_required
def live_session(request):
    current_time = timezone.now()
    sessions = LiveSession.objects.filter(
        is_visible=True,
        status='scheduled',
        scheduled_at__gte=current_time
    ).order_by('scheduled_at')

    if request.user.profile.user_type == 'student':
        enrolled_courses = CourseEnrollment.objects.filter(
            user=request.user, status='approved'
        ).values_list('course_id', flat=True)
        sessions = [
            {
                'id': session.id,
                'title': session.title,
                'course': session.course.title,
                'scheduled_at': session.scheduled_at,
                'session_type': session.session_type,
                'can_join': session.is_open_to_all or session.course.id in enrolled_courses
            }
            for session in sessions
        ]
    elif request.user.profile.user_type == 'facilitator':
        sessions = sessions.filter(course__facilitator=request.user)
        sessions = [
            {
                'id': session.id,
                'title': session.title,
                'course': session.course.title,
                'scheduled_at': session.scheduled_at,
                'session_type': session.session_type,
                'can_join': True
            }
            for session in sessions
        ]
    else:  # Admins
        sessions = [
            {
                'id': session.id,
                'title': session.title,
                'course': session.course.title,
                'scheduled_at': session.scheduled_at,
                'session_type': session.session_type,
                'can_join': True
            }
            for session in sessions
        ]

    return render(request, 'core/live_session.html', {
        'sessions': sessions,
        'logo_base64': settings.LOGO_BASE64
    })
    
    
@login_required
def join_session(request, session_id):
    session = get_object_or_404(LiveSession, id=session_id, is_visible=True, status__in=['scheduled', 'ongoing'])
    if request.user.profile.user_type == 'student':
        if not session.is_open_to_all:
            enrolled_courses = CourseEnrollment.objects.filter(
                user=request.user, status='approved'
            ).values_list('course_id', flat=True)
            if session.course.id not in enrolled_courses:
                messages.error(request, 'You are not authorized to join this session.')
                return redirect('student_dashboard')
    SessionAttendance.objects.create(
        session=session,
        user=request.user
    )
    AuditLog.objects.create(
        user=request.user,
        action='Session Joined',
        details=f"Joined session {session.title}"
    )
    Notification.objects.create(
        user=session.created_by,
        type='general',
        message=f"{request.user.username} joined your session '{session.title}'."
    )
    return redirect(session.zoom_url)
def landing(request):
    courses = Course.objects.all()
    featured_portfolios = Portfolio.objects.filter(is_public=True, is_featured=True)
    return render(request, 'core/landing.html', {'courses': courses, 'featured_portfolios': featured_portfolios, 'logo_base64': settings.LOGO_BASE64})

@login_required
def student_dashboard(request):
    user = request.user
    enrollment = CourseEnrollment.objects.filter(user=user).first()
    course_title = escape(enrollment.course.title) if enrollment else "No Course Enrolled"
    if enrollment and enrollment.status == 'pending':
        course_title += " (Pending Payment/Approval)"
    
    cohort = Cohort.objects.filter(students=user).first()
    cohort_name = cohort.name if cohort else "Not Assigned"
    whatsapp_link = cohort.whatsapp_link if cohort and cohort.whatsapp_link else None
    
    assignments = Assignment.objects.filter(course__courseenrollment__user=user, course__courseenrollment__status='approved')[:3]
    projects = Project.objects.filter(course__courseenrollment__user=user, course__courseenrollment__status='approved')[:3]
    assignment_submission_count = user.submission_set.filter(assignment__isnull=False).count()
    
    live_sessions = LiveSession.objects.filter(course__courseenrollment__user=user, status='scheduled')[:3]
    
    performance_records = PerformanceRecord.objects.filter(user=user).order_by('-month')[:5]
    performance_record_count = performance_records.count()
    
    portfolio = Portfolio.objects.filter(user=user).first()
    
    latest_attempt = user.quizattempt_set.filter(quiz__title__icontains='onboarding').order_by('-attempted_at').first()
    quiz_score_percentage = (latest_attempt.score / 15 * 100) if latest_attempt else 0
    quiz_passed = latest_attempt.passed if latest_attempt else False
    
    context = {
        'user': user,
        'course_title': course_title,
        'enrollment_status': enrollment.status if enrollment else None,
        'cohort': cohort,
        'cohort_name': cohort_name,
        'whatsapp_link': whatsapp_link,
        'assignments': assignments,
        'projects': projects,
        'live_sessions': live_sessions,
        'assignment_submission_count': assignment_submission_count,
        'performance_records': performance_records,
        'performance_record_count': performance_record_count,
        'portfolio': portfolio,
        'latest_attempt': latest_attempt,
        'quiz_score_percentage': quiz_score_percentage,
        'quiz_passed': quiz_passed,
        'is_student': user.profile.user_type == 'student',
        'student_passcode': user.profile.student_passcode if user.profile.user_type == 'student' else None,
    }
    return render(request, 'core/student_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def payment_approval(request):
    slips = PaymentSlip.objects.all().order_by('-uploaded_at')
    return render(request, 'core/payment_approval.html', {'slips': slips, 'logo_base64': settings.LOGO_BASE64})

@login_required
@user_passes_test(lambda u: u.is_staff)
def approve_payment(request, slip_id):
    slip = get_object_or_404(PaymentSlip, id=slip_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['approved', 'rejected']:
            slip.status = status
            slip.save()
            if status == 'approved':
                # Approve the corresponding enrollment
                enrollment = CourseEnrollment.objects.filter(
                    user=slip.user,
                    course=slip.course,
                    status='pending'
                ).first()
                if enrollment:
                    enrollment.status = 'approved'
                    enrollment.save()
                    logger.info(f"Approved enrollment for {slip.user.username} in {slip.course.title}")
            Notification.objects.create(
                user=slip.user,
                type='slip',
                message=f"Your payment slip for {slip.course.title} has been {status}."
            )
            AuditLog.objects.create(
                user=request.user,
                action='Payment Slip Status Updated',
                details=f"Slip {slip.id} for {slip.user.username} set to {status}"
            )
            messages.success(request, f'Payment slip {status}.')
    return redirect('payment_approval')
@login_required
def upload_payment_slip(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = PaymentSlipForm(request.POST, request.FILES)
        if form.is_valid():
            slip = form.save(commit=False)
            slip.user = request.user
            slip.course = course
            slip.save()
            Notification.objects.create(
                user=request.user,
                type='slip',
                message=f"Your payment slip for {course.title} has been uploaded."
            )
            AuditLog.objects.create(
                user=request.user,
                action='Payment Slip Uploaded',
                details=f"Slip for course {course.title}"
            )
            messages.success(request, 'Payment slip uploaded successfully.')
            return redirect('student_dashboard')
    else:
        form = PaymentSlipForm()
    return render(request, 'core/upload_payment_slip.html', {'form': form, 'course': course, 'logo_base64': settings.LOGO_BASE64})

@login_required
@user_passes_test(lambda u: u.is_staff)
@otp_required
def submit_salary(request):
    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        account_number = request.POST.get('account_number')
        routing_number = request.POST.get('routing_number')
        if not all([bank_name, account_number, routing_number]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'core/submit_salary.html', {'logo_base64': settings.LOGO_BASE64})
        submission = SalarySubmission.objects.create(
            facilitator=request.user,
            bank_name=bank_name,
            account_number=account_number,
            routing_number=routing_number
        )
        Notification.objects.create(
            user=request.user,
            type='salary',
            message='Your salary submission has been received and is pending review.'
        )
        AuditLog.objects.create(
            user=request.user,
            action='Salary Submission',
            details=f"Submitted salary details for {request.user.username}"
        )
        messages.success(request, 'Salary submission received and pending review.')
        return redirect('facilitator_application_dashboard')
    return render(request, 'core/submit_salary.html', {'logo_base64': settings.LOGO_BASE64})

@login_required
def live_session(request):
    current_time = timezone.now()
    sessions = LiveSession.objects.filter(
        is_visible=True,
        status='scheduled',
        scheduled_at__gte=current_time
    ).order_by('scheduled_at')

    # For students, mark which sessions they can join
    if request.user.profile.user_type == 'student':
        enrolled_courses = CourseEnrollment.objects.filter(
            user=request.user, status='approved'
        ).values_list('course_id', flat=True)
        sessions = [
            {
                'id': session.id,
                'title': session.title,
                'course': session.course.title,
                'scheduled_at': session.scheduled_at,
                'session_type': session.session_type,
                'can_join': session.is_open_to_all or session.course.id in enrolled_courses
            }
            for session in sessions
        ]
    elif request.user.profile.user_type == 'facilitator':
        sessions = sessions.filter(course__facilitator=request.user)
        sessions = [
            {
                'id': session.id,
                'title': session.title,
                'course': session.course.title,
                'scheduled_at': session.scheduled_at,
                'session_type': session.session_type,
                'can_join': True  # Facilitators can join their own sessions
            }
            for session in sessions
        ]
    else:  # Admins
        sessions = [
            {
                'id': session.id,
                'title': session.title,
                'course': session.course.title,
                'scheduled_at': session.scheduled_at,
                'session_type': session.session_type,
                'can_join': True  # Admins can join any session
            }
            for session in sessions
        ]

    return render(request, 'core/live_session.html', {
        'sessions': sessions,
        'logo_base64': settings.LOGO_BASE64
    })
@login_required
def join_session(request, session_id):
    session = get_object_or_404(LiveSession, id=session_id, is_visible=True, status__in=['scheduled', 'ongoing'])
    if request.user.profile.user_type == 'student':
        if not session.is_open_to_all:
            enrolled_courses = CourseEnrollment.objects.filter(
                user=request.user, status='approved'
            ).values_list('course_id', flat=True)
            if session.course.id not in enrolled_courses:
                messages.error(request, 'You are not authorized to join this session.')
                return redirect('student_dashboard')
    # Admins and facilitators can join any session
    SessionAttendance.objects.create(
        session=session,
        user=request.user
    )
    AuditLog.objects.create(
        user=request.user,
        action='Session Joined',
        details=f"Joined session {session.title}"
    )
    Notification.objects.create(
        user=session.created_by,
        type='general',
        message=f"{request.user.username} joined your session '{session.title}'."
    )
    return redirect(session.zoom_url)
def recap_session(request):
    recaps = SessionRecap.objects.all()
    return render(request, 'core/recap_session.html', {'recaps': recaps, 'logo_base64': settings.LOGO_BASE64})

@login_required
def inbox(request):
    messages_list = Message.objects.filter(recipient=request.user).order_by('-sent_at')
    return render(request, 'core/inbox.html', {'messages': messages_list, 'logo_base64': settings.LOGO_BASE64})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    slips = PaymentSlip.objects.filter(status='pending').order_by('-uploaded_at')
    salary_submissions = SalarySubmission.objects.filter(status='pending').order_by('-submitted_at')
    portfolios = Portfolio.objects.all()
    quiz_attempts = QuizAttempt.objects.order_by('-attempted_at')
    performance_records = PerformanceRecord.objects.all()
    student_count = User.objects.filter(is_staff=False).count()
    course_count = Course.objects.count()
    slip_count = slips.count()
    audit_logs = AuditLog.objects.order_by('-timestamp')[:5]
    portfolio_views = AuditLog.objects.filter(action='Portfolio Viewed').count()
    notification_settings = {
        'assignment_notifications': True,
        'payment_notifications': True
    }
    payment_detail = PaymentDetail.objects.first() or PaymentDetail.objects.create()
    courses = Course.objects.all().order_by('title')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_payment_details':
            bank_name = request.POST.get('bank_name', '').strip()
            bank_account_number = request.POST.get('bank_account_number', '').strip()
            bank_account_name = request.POST.get('bank_account_name', '').strip()
            momo_name = request.POST.get('momo_name', '').strip()
            momo_number = request.POST.get('momo_number', '').strip()
            momo_provider = request.POST.get('momo_provider', '').strip()

            errors = []
            if not bank_name or not bank_account_number or not bank_account_name:
                errors.append("All bank details are required.")
            if not momo_name or not momo_number or not momo_provider:
                errors.append("All MoMo details are required.")
            
            try:
                if momo_number:
                    phone = parse(momo_number)
                    if not is_valid_number(phone):
                        errors.append("Invalid MoMo phone number.")
            except NumberParseException:
                errors.append("Invalid MoMo phone number format.")

            if errors:
                for error in errors:
                    messages.error(request, error)
            else:
                payment_detail.bank_name = bank_name
                payment_detail.bank_account_number = bank_account_number
                payment_detail.bank_account_name = bank_account_name
                payment_detail.momo_name = momo_name
                payment_detail.momo_number = momo_number
                payment_detail.momo_provider = momo_provider
                payment_detail.updated_by = request.user
                payment_detail.save()
                messages.success(request, "Payment details updated successfully.")
                AuditLog.objects.create(
                    user=request.user,
                    action='Payment Details Updated',
                    details=f"Updated payment details by {request.user.username}"
                )

        elif action == 'update_course_price':
            course_id = request.POST.get('course_id')
            price = request.POST.get('price', '').strip()
            course = get_object_or_404(Course, id=course_id)
            
            try:
                price = Decimal(price)
                if price < 0:
                    raise InvalidOperation
                course.price = price
                course.save()
                messages.success(request, f"Price for {course.title} updated to ₦{price:,.2f}.")
                AuditLog.objects.create(
                    user=request.user,
                    action='Course Price Updated',
                    details=f"Updated price for {course.title} to ₦{price:,.2f}"
                )
            except (InvalidOperation, ValueError):
                messages.error(request, f"Invalid price for {course.title}. Please enter a valid number.")

        return redirect('admindashboard')

    return render(request, 'core/admindashboard.html', {
        'slips': slips,
        'salary_submissions': salary_submissions,
        'portfolios': portfolios,
        'quiz_attempts': quiz_attempts,
        'performance_records': performance_records,
        'student_count': student_count,
        'course_count': course_count,
        'slip_count': slip_count,
        'audit_logs': audit_logs,
        'portfolio_views': portfolio_views,
        'notification_settings': notification_settings,
        'payment_detail': payment_detail,
        'courses': courses,
        'logo_base64': settings.LOGO_BASE64
    })
@login_required
@user_passes_test(lambda u: u.is_staff)
def verify_admin_access(request):
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    devices = devices_for_user(request.user)
    if not devices:
        return redirect('two_factor_setup')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        verified = False
        for device in devices:
            if device.verify_token(otp_code):
                verified = True
                break
        if verified:
            AuditLog.objects.create(
                user=request.user,
                action='2FA Verified',
                details='Successful 2FA verification'
            )
            request.session['2fa_verified'] = True
            return JsonResponse({'status': 'success', 'redirect': '/admindashboard/'})
        else:
            AuditLog.objects.create(
                user=request.user,
                action='2FA Failed',
                details='Failed 2FA verification attempt'
            )
            return render(request, 'core/two_factor_verify.html', {'error': 'Invalid OTP code', 'logo_base64': settings.LOGO_BASE64})
    
    return render(request, 'core/two_factor_verify.html', {'logo_base64': settings.LOGO_BASE64})

@login_required
@user_passes_test(lambda u: u.is_staff)
def feature_portfolio(request, portfolio_id):
    portfolio = get_object_or_404(Portfolio, id=portfolio_id)
    if request.method == 'POST':
        portfolio.is_featured = 'is_featured' in request.POST
        portfolio.save()
        AuditLog.objects.create(
            user=request.user,
            action='Portfolio Featured Status Updated',
            details=f"Portfolio {portfolio.user.username} set to featured: {portfolio.is_featured}"
        )
        messages.success(request, 'Portfolio updated successfully.')
    return redirect('admindashboard')

@login_required
@user_passes_test(lambda u: u.is_staff)
def toggle_notifications(request):
    if request.method == 'POST':
        AuditLog.objects.create(
            user=request.user,
            action='Notification Settings Updated',
            details='Updated notification preferences'
        )
        messages.success(request, 'Notification settings updated.')
    return redirect('admindashboard')

@login_required
@user_passes_test(lambda u: u.is_staff)
def grade_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == 'POST':
        grade = request.POST.get('grade')
        feedback = request.POST.get('feedback')
        submission.grade = float(grade) if grade else None
        submission.feedback = feedback
        submission.save()
        Notification.objects.create(
            user=submission.user,
            type='assignment',
            message=f"Your submission for {submission.assignment.title if submission.assignment else submission.project.title} has been graded: {grade}/100."
        )
        AuditLog.objects.create(
            user=request.user,
            action='Submission Graded',
            details=f"Graded submission {submission.id} with {grade}"
        )
        messages.success(request, 'Submission graded successfully.')
    return redirect('facilitator_application_dashboard')

@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_performance(request, record_id):
    record = get_object_or_404(PerformanceRecord, id=record_id)
    if request.method == 'POST':
        record.warning_issued = 'warning_issued' in request.POST
        record.suspended = 'suspended' in request.POST
        record.reward_earned = request.POST.get('reward_earned', '')
        record.save()
        if record.warning_issued:
            Notification.objects.create(
                user=record.user,
                type='performance',
                message=f"Warning: Your performance in Month {record.month} is below 25%."
            )
        if record.suspended:
            Notification.objects.create(
                user=record.user,
                type='performance',
                message=f"You have been suspended due to low performance in Month {record.month}."
            )
        if record.reward_earned:
            Notification.objects.create(
                user=record.user,
                type='performance',
                message=f"Congratulations! You earned a {record.reward_earned} for Month {record.month}."
            )
        AuditLog.objects.create(
            user=request.user,
            action='Performance Record Updated',
            details=f"Updated record for {record.user.username}, Month {record.month}"
        )
        messages.success(request, 'Performance record updated.')
    return redirect('admindashboard')

@login_required
@user_passes_test(lambda u: u.is_staff)
def salary_approval(request):
    submissions = SalarySubmission.objects.all().order_by('-submitted_at')
    return render(request, 'core/salary_approval.html', {'submissions': submissions, 'logo_base64': settings.LOGO_BASE64})

@login_required
@user_passes_test(lambda u: u.is_staff)
def approve_salary(request, submission_id):
    submission = get_object_or_404(SalarySubmission, id=submission_id)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['approved', 'rejected']:
            submission.status = status
            if status == 'approved':
                submission.payment_date = timezone.now()
            submission.save()
            Notification.objects.create(
                user=submission.facilitator,
                type='salary',
                message=f"Your salary submission has been {status}."
            )
            AuditLog.objects.create(
                user=request.user,
                action='Salary Submission Status Updated',
                details=f"Submission {submission.id} for {submission.facilitator.username} set to {status}"
            )
            messages.success(request, f'Salary submission {status}.')
    return redirect('salary_approval')

@login_required
def two_factor_setup(request):
    if not request.user.is_superuser:
        return redirect('student_dashboard')
    
    device, created = TOTPDevice.objects.get_or_create(user=request.user, name='default')
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        if device.verify_token(otp_code):
            device.confirmed = True
            device.save()
            Notification.objects.create(
                user=request.user,
                type='general',
                message='Two-Factor Authentication has been enabled.'
            )
            AuditLog.objects.create(
                user=request.user,
                action='2FA Setup',
                details='2FA enabled for admin account'
            )
            return redirect('verify_admin_access')
        else:
            return render(request, 'core/two_factor_setup.html', {
                'qr_code_url': get_qr_code_url(request.user, device),
                'totp_secret': device.config_url.split('secret=')[1].split('&')[0],
                'error': 'Invalid OTP code',
                'logo_base64': settings.LOGO_BASE64
            })
    
    return render(request, 'core/two_factor_setup.html', {
        'qr_code_url': get_qr_code_url(request.user, device),
        'totp_secret': device.config_url.split('secret=')[1].split('&')[0],
        'logo_base64': settings.LOGO_BASE64
    })

def get_qr_code_url(user, device):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(device.config_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()

@login_required
def course_library(request):
    materials = CourseMaterial.objects.filter(course__cohort__students=request.user)
    query = request.GET.get('q')
    if query:
        materials = materials.filter(title__icontains=query) | materials.filter(course__title__icontains=query)
    return render(request, 'core/course_library.html', {'materials': materials, 'logo_base64': settings.LOGO_BASE64})

@login_required
def log_material_access(request, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id)
    AuditLog.objects.create(
        user=request.user,
        action='Material Accessed',
        details=f"Viewed material {material.title} for course {material.course.title}"
    )
    return JsonResponse({'status': 'success'})

@login_required
def edit_portfolio(request):
    portfolio, created = Portfolio.objects.get_or_create(
        user=request.user,
        defaults={
            'name': request.user.username,
            'bio': '',
            'github_url': '',
            'skills': '',
            'projects': '',
            'certificates': ''
        }
    )
    if request.method == 'POST':
        form = PortfolioForm(request.POST, instance=portfolio)
        if form.is_valid():
            form.save()
            Notification.objects.create(
                user=request.user,
                type='general',
                message='Your portfolio has been updated and is under admin review.'
            )
            AuditLog.objects.create(
                user=request.user,
                action='Portfolio Updated',
                details=f"Portfolio for {request.user.username} updated"
            )
            messages.success(request, 'Portfolio updated successfully.')
            return redirect('student_dashboard')
    else:
        form = PortfolioForm(instance=portfolio)
    return render(request, 'core/edit_portfolio.html', {'portfolio': portfolio, 'form': form, 'logo_base64': settings.LOGO_BASE64})

def portfolio_view(request, username):
    if not User.objects.filter(username=username).exists():
        logger.warning(f"Portfolio view attempted for non-existent user: {username}")
        messages.error(request, f"No user with username {username} exists.")
        return render(request, 'core/portfolio_unavailable.html', {
            'username': username,
            'logo_base64': settings.LOGO_BASE64
        })
    try:
        portfolio = Portfolio.objects.get(user__username=username, is_public=True)
    except Portfolio.DoesNotExist:
        logger.warning(f"Portfolio view attempted for non-existent or non-public portfolio: {username}")
        messages.error(request, f"The portfolio for {username} is not available or not public.")
        return render(request, 'core/portfolio_unavailable.html', {
            'username': username,
            'logo_base64': settings.LOGO_BASE64
        })
    AuditLog.objects.create(
        user=None,
        action='Portfolio Viewed',
        details=f"Portfolio of {username} viewed"
    )
    return render(request, 'core/portfolio_view.html', {
        'portfolio': portfolio,
        'logo_base64': settings.LOGO_BASE64
    })
@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')[:5]
    data = [{
        'message': n.message,
        'type': n.type,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
    } for n in notifications]
    return JsonResponse({'notifications': data})

@login_required
def onboarding_quiz(request):
    if request.user.profile.user_type != 'student':
        messages.error(request, 'Only students can take the onboarding quiz.')
        return redirect('student_dashboard')
    
    if request.user.profile.onboarding_quiz_completed:
        return redirect('student_dashboard')
    
    social_media_links = {
        'facebook': 'https://www.facebook.com/multitechspace',
        'twitter': 'https://x.com/firstso14272266?s=21',
        'instagram': 'https://www.instagram.com/valentineucheena?igsh=MXgzZzE0Nmh1Zzg5aQ%3D%3D&utm_source=qr',
        'linkedin': 'linkedin.com/in/valentine-uchenna-678355284'
    }
    
    if request.method == 'POST':
        form = OnboardingQuizForm(request.POST)
        logger.debug(f"Form data: {request.POST}")
        if form.is_valid():
            OnboardingQuizResponse.objects.create(
                user=request.user,
                has_laptop=form.cleaned_data['has_laptop'],
                occupation=form.cleaned_data['occupation'],
                bio=form.cleaned_data['bio'],
                followed_social_media=form.cleaned_data.get('followed_social_media', False)
            )
            request.user.profile.onboarding_quiz_completed = True
            request.user.profile.save()
            Notification.objects.create(
                user=request.user,
                type='general',
                message='You have completed the onboarding quiz.'
            )
            AuditLog.objects.create(
                user=request.user,
                action='Onboarding Quiz Completed',
                details=f"User {request.user.username} completed onboarding quiz"
            )
            messages.success(request, 'Onboarding quiz submitted successfully.')
            return redirect('student_dashboard')
        else:
            logger.warning(f"Onboarding quiz failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = OnboardingQuizForm()
    
    return render(request, 'core/onboarding_quiz.html', {
        'form': form,
        'social_media_links': social_media_links,
        'logo_base64': settings.LOGO_BASE64
    })

@login_required
def facilitator_application(request):
    if request.user.profile.user_type != 'facilitator':
        return JsonResponse({'success': False, 'message': 'Only facilitators can access this application.'}, status=403)
    
    approved_apps = FacilitatorApplication.objects.filter(user=request.user, status='approved').count()
    applications = FacilitatorApplication.objects.filter(user=request.user)
    
    if approved_apps:
        messages.info(request, 'You are already an applied facilitator for a course. Contact the admin to apply apply for additional courses.')
        return redirect('facilitator_application_dashboard')

    if request.method == 'POST':
        form = FacilitatorProfileForm(request.POST)
        if form.is_valid():
            profile = request.user.profile
            profile.linkedin_url = form.cleaned_data['linkedin']
            profile.twitter_url = form.cleaned_data['twitter']
            profile.github_url = form.cleaned_data['github']
            profile.facebook_url = form.cleaned_data['facebook']
            profile.internship_available = form.cleaned_data['internship_available']
            profile.facilitator_profile_completed = True
            profile.save()
            new_course = form.cleaned_data['course']
            existing_application = FacilitatorApplication.objects.filter(user=request.user, course=new_course).first()
            if existing_application:
                messages.warning(request, f'You have already applied for {new_course.title}.')
            else:
                FacilitatorApplication.objects.create(
                    user=request.user,
                    course=new_course,
                    status='pending'
                )
                logger.info(f"Created application for {request.user.username} for course {new_course.title}")
                notification_message = f'Submitted application to facilitate {new_course.title}.'
                if new_course.facilitator:
                    notification_message += f' Note: This course has a facilitator ({new_course.facilitator.username}). Application pending review.'
                Notification.objects.create(
                    user=request.user,
                    type='application',
                    message=notification_message
                )
                messages.success(request, 'Application submitted successfully.')
            return redirect('facilitator_application_dashboard')
        else:
            logger.warning(f"Facilitator application failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
            return JsonResponse({'success': False, 'message': form.errors.as_json()}, status=400)
    else:
        form = FacilitatorProfileForm()
    
    return render(request, 'core/facilitator_application.html', {
        'form': form,
        'applications': applications,
        'logo_base64': settings.LOGO_BASE64
    })

@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    if request.method == 'POST':
        submission_url = request.POST.get('submission_url', '').strip()
        if not submission_url:
            messages.error(request, 'Submission URL is required.')
            return render(request, 'core/submit_assignment.html', {'assignment': assignment, 'logo_base64': settings.LOGO_BASE64})
        Submission.objects.create(
            user=request.user,
            assignment=assignment,
            type='submission',
            submission_url=submission_url
        )
        logger.info(f"Submitted assignment {assignment.title} by {request.user.username}")
        Notification.objects.create(
            user=request.user,
            type='submission',
            message=f"Your submission for {assignment.title} has been received."
        )
        AuditLog.objects.create(
            user=request.user,
            action='assignment_submission',
            details=f"Submitted assignment {assignment.title}"
        )
        messages.success(request, 'Assignment submitted successfully.')
        return redirect('student_dashboard')
    return render(request, 'core/submit_assignment.html', {'assignment': assignment, 'logo_base64': settings.LOGO_BASE64})

@login_required
def submit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    # Check if user is enrolled in the course
    if not CourseEnrollment.objects.filter(user=request.user, course=project.course, status='approved').exists():
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        submission_url = request.POST.get('submission_url', '').strip()
        if not submission_url:
            messages.error(request, 'Submission URL is required.')
            return render(request, 'core/submit_project.html', {'project': project, 'logo_base64': settings.LOGO_BASE64})
        
        # Validate URL
        validate = URLValidator()
        try:
            validate(submission_url)
        except ValidationError:
            messages.error(request, 'Please provide a valid URL.')
            return render(request, 'core/submit_project.html', {'project': project, 'logo_base64': settings.LOGO_BASE64})
        
        Submission.objects.create(
            user=request.user,
            project=project,
            type='submission',
            submission_url=submission_url
        )
        logger.info(f"Submitted project {project.title} by {request.user.username}")
        Notification.objects.create(
            user=request.user,
            type='submission',
            message=f"Your submission for {project.title} has been received."
        )
        AuditLog.objects.create(
            user=request.user,
            action='project_submission',
            details=f"Submitted project {project.title}"
        )
        messages.success(request, 'Project submitted successfully.')
        return redirect('student_dashboard')
    
    return render(request, 'core/submit_project.html', {'project': project, 'logo_base64': settings.LOGO_BASE64})

@login_required
@user_passes_test(lambda u: u.is_staff or u.profile.user_type == 'facilitator')
def facilitator_application_dashboard(request):
    assigned_courses = Course.objects.filter(facilitator=request.user)
    available_courses = Course.objects.filter(facilitator__isnull=True)
    submissions = (
        Submission.objects.filter(assignment__course__facilitator=request.user) |
        Submission.objects.filter(project__course__facilitator=request.user)
    )
    latest_submission = submissions.order_by('-created_at').first()
    applications = FacilitatorApplication.objects.filter(user=request.user)
    return render(request, 'core/facilitator_dashboard.html', {
        'assigned_courses': assigned_courses,
        'available_courses': available_courses,
        'submissions': submissions,
        'latest_submission': latest_submission,
        'applications': applications,
        'logo_base64': settings.LOGO_BASE64
    })

@login_required
def discussion_board(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id, students=request.user)
    posts = DiscussionPost.objects.filter(cohort=cohort).order_by('-created_at')
    return render(request, 'core/discussion_board.html', {
        'cohort': cohort,
        'posts': posts,
        'whatsapp_link': cohort.whatsapp_link or None,
        'logo_base64': settings.LOGO_BASE64
    })
    cohort = get_object_or_404(Cohort, id=cohort_id, students=request.user)
    posts = DiscussionPost.objects.filter(cohort=cohort).order_by('-created_at')
    return render(request, 'core/discussion_board.html', {
        'cohort': cohort,
        'posts': posts,
        'whatsapp_link': cohort.whatsapp_link or None,
        'logo_base64': settings.LOGO_BASE64
    })
@login_required
def create_discussion_post(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id, students=request.user)
    if request.method == 'POST':
        form = DiscussionPostForm(request.POST)
        if form.is_valid():
            post = DiscussionPost.objects.create(
                cohort=cohort,
                user=request.user,
                title=form.cleaned_data['title'],
                content=form.cleaned_data['content']
            )
            logger.info(f"Created post {post.title} by {request.user.username} in cohort {cohort.name}")
            Notification.objects.create(
                user=request.user,
                type='general',
                message=f'Your post "{post.title}" has been created.'
            )
            AuditLog.objects.create(
                user=request.user,
                action='post',
                details=f'Post {post.title} created in cohort {cohort.id}'
            )
            messages.success(request, 'Post created successfully.')
            return redirect('discussion_board', cohort_id=cohort_id)
        else:
            messages.error(request, 'Please provide both title and content.')
    else:
        form = DiscussionPostForm()
    return render(request, 'core/create_discussion', {'form': form, 'cohort': cohort, 'logo_base64': settings.LOGO_BASE64})@login_required
def add_discussion_comment(request, post_id):
    post = get_object_or_404(DiscussionPost, id=post_id)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if not content:
            messages.error(request, 'Comment cannot be empty.')
        else:
            comment = DiscussionComment.objects.create(
                post=post,
                user=request.user,
                content=content
            )
            logger.info(f"Added comment by {request.user.username} on post {post.title}")
            Notification.objects.create(
                user=post.user,
                type='comment',
                message=f"{request.user.username} commented on your post '{post.title}'."
            )
            AuditLog.objects.create(
                user=request.user,
                action='comment_post_comment',
                details=f'Commented on post {post.title}'
            )
            messages.success(request, 'Comment added successfully.')
    return redirect('discussion_board', cohort_id=post.cohort.id)

@login_required
def leaderboard(request):
    leaderboard = PerformanceRecord.objects.values('user__username').annotate(
        total_score=Sum('score')
    ).order_by('-total_score')[:10]
    return render(request, 'core/leaderboard.html', {'leaderboard': leaderboard, 'logo_base64': settings.LOGO_BASE64})

@login_required
def assign_student_leader(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id, facilitator=request.user)
    if request.method == 'POST':
        student_id = request.POST.get('student_id', '')
        if not student_id:
            messages.error(request, 'Please select a student.')
            return render(request, 'core/assign_leader.html', {'cohort': cohort, 'students': cohort.students.all(), 'logo_base64': settings.LOGO_BASE64})
        student = get_object_or_404(User, id=student_id, cohorts=cohort)
        cohort.student_leader = student
        cohort.save()
        logger.info(f"Assigned {student.username} as student leader for {cohort.name} by {request.user.username}")
        Notification.objects.create(
            user=student,
            type='user',
            message=f"You have been assigned as the student leader for cohort {cohort.name}."
        )
        AuditLog.objects.create(
            user=request.user,
            action='student_leader_assignment',
            details=f"Assigned {student.username} as student leader for {cohort.name}"
        )
        messages.success(request, f"{student.username} assigned as student leader.")
        return redirect('facilitator_application_dashboard')
    students = cohort.students.all()
    return render(request, 'core/assign_leader.html', {'cohort': cohort, 'students': students, 'logo_base64': settings.LOGO_BASE64})
@login_required
def apply_for_course(request):
    if request.user.profile.user_type != 'facilitator':
        return JsonResponse({'error': 'Only facilitators can apply for courses.'}, status=403)
    
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        if not course_id:
            return JsonResponse({'error': 'Course ID is required.'}, status=400)
        course = get_object_or_404(Course, id=course_id)
        if FacilitatorApplication.objects.filter(user=request.user, status='approved').exists():
            return JsonResponse({
                'error': 'You are already an approved facilitator for a course. Contact the admin to apply for additional courses.'
            }, status=403)
        application, created = FacilitatorApplication.objects.get_or_create(
            user=request.user,
            course=course,
            defaults={'status': 'pending'}
        )
        if not created:
            return JsonResponse({
                'error': 'You have already applied for this course.'
            }, status=400)
        logger.info(f"Application for {course.title} by {request.user.username}")
        notification_message = f'Submitted application to facilitate {course.title}.'
        if course.facilitator:
            notification_message += f' Note: This course has a facilitator ({course.title}).'
        Notification.objects.create(
            user=request.user,
            type='application',
            message=notification_message
        )
        AuditLog.objects.create(
            user=request.user,
            action='course_application',
            details=f'Application for {course.title}'
        )
        return JsonResponse({
            'message': f'Application for {course.title} submitted successfully.'
        })
    return redirect('course_list')

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.prefetch_related('answers')
    if request.method == 'POST':
        score = 0
        total_questions = questions.count()
        for question in questions:
            selected_answer_id = request.POST.get(f'q_{question.id}')
            if selected_answer_id and Answer.objects.filter(id=selected_answer_id, question=question, is_correct=True).exists():
                score += 1
        passed = score >= total_questions / 2
        QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            score=score,
            passed=passed
        )
        messages.success(request, f'Quiz completed! Score: {score}/{total_questions}')
        return redirect('student_dashboard')
    return render(request, 'core/take_quiz.html', {'quiz': quiz, 'questions': questions})

@login_required
@user_passes_test(lambda u: u.is_staff or u.profile.user_type == 'facilitator')
def upload_material(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.profile.user_type == 'facilitator' and course.facilitator != request.user:
        messages.error(request, 'You can only upload materials for your courses.')
        return redirect('facilitator_dashboard')
    if request.method == 'POST':
        title = request.POST.get('title')
        file = request.FILES.get('file')
        if title and file:
            CourseMaterial.objects.create(course=course, title=title, file=file)
            messages.success(request, 'Material uploaded successfully.')
            return redirect('course_library')
        messages.error(request, 'Title and file are required.')
    return render(request, 'core/upload_material.html', {'course': course})

@login_required
@user_passes_test(lambda u: u.is_staff or u.profile.user_type == 'facilitator')
def create_assignment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.profile.user_type == 'facilitator' and course.facilitator != request.user:
        messages.error(request, 'You can only create assignments for your courses.')
        return redirect('facilitator_dashboard')
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        due_date = request.POST.get('due_date')
        if title and description and due_date:
            Assignment.objects.create(
                course=course,
                title=title,
                description=description,
                due_date=timezone.datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
            )
            messages.success(request, 'Assignment created successfully.')
            return redirect('facilitator_dashboard')
        messages.error(request, 'All fields are required.')
    return render(request, 'core/create_assignment.html', {'course': course})

@login_required
def edit_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = CustomRegistrationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.email = form.cleaned_data['email']
            request.user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('student_dashboard')
    else:
        form = CustomRegistrationForm(instance=profile, initial={'email': request.user.email})
    return render(request, 'core/edit_profile.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            try:
                course = form.save()
                logger.info(f"Course {course.title} created by {request.user.username}")
                
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    action='Course Created',
                    details=f"Created course {course.title} with price ₦{course.price:,.2f}"
                )
                
                # Notify admin
                Notification.objects.create(
                    user=request.user,
                    type='general',
                    message=f"Course '{course.title}' has been successfully created."
                )
                
                # Notify approved facilitators
                facilitators = User.objects.filter(
                    profile__user_type='facilitator',
                    facilitatorapplication__status='approved'
                ).distinct()
                notifications = [
                    Notification(
                        user=facilitator,
                        type='general',
                        message=f"A new course '{course.title}' is available. Apply to facilitate it."
                    )
                    for facilitator in facilitators
                ]
                Notification.objects.bulk_create(notifications)
                
                messages.success(request, f"Course '{course.title}' created successfully.")
                return redirect('admin_dashboard')
            except Exception as e:
                logger.error(f"Failed to create course: {str(e)}")
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            logger.warning(f"Course creation failed: {form.errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm()
    
    return render(request, 'core/create_course.html', {
        'form': form,
        'logo_base64': settings.LOGO_BASE64
    })