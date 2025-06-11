from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
import random
import string

class Profile(models.Model):
    USER_TYPES = (
        ('student', 'Student'),
        ('facilitator', 'Facilitator'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    mobile_number = PhoneNumberField(blank=True, null=True, help_text="Include country code, e.g., +2341234567890")
    country = models.CharField(max_length=100, blank=True, null=True)
    student_passcode = models.CharField(max_length=4, unique=True, blank=True, null=True, help_text="Unique 4-digit passcode")
    onboarding_quiz_completed = models.BooleanField(default=False)
    facilitator_profile_completed = models.BooleanField(default=False)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)
    internship_available = models.BooleanField(default=False)

    def generate_passcode(self):
        while True:
            passcode = ''.join(random.choices(string.digits, k=4))
            if not Profile.objects.filter(student_passcode=passcode).exists():
               return passcode  # just return it without saving


    def save(self, *args, **kwargs):
        if self.user_type == 'student' and not self.student_passcode:
           self.student_passcode = self.generate_passcode()
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.user.username} - {self.user_type}"
class Course(models.Model):
    LEVEL_CHOICES = (
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.IntegerField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    facilitator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    def __str__(self):
        return self.title
class Cohort(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    facilitator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cohort_facilitator')
    students = models.ManyToManyField(User, related_name='cohorts')
    student_leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_cohorts')
    whatsapp_link = models.URLField(blank=True, null=True)
    facebook_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.course.title}"
    
class CourseEnrollment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class OnboardingQuizResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    has_laptop = models.BooleanField()
    occupation = models.CharField(max_length=100)
    bio = models.TextField()
    followed_social_media = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Onboarding Response"

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    github_url = models.URLField(blank=True)
    skills = models.TextField(blank=True)
    projects = models.TextField(blank=True)
    certificates = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Portfolio"

class Notification(models.Model):
    TYPE_CHOICES = (
        ('general', 'General'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('slip', 'Payment Slip'),
        ('salary', 'Salary'),
        ('performance', 'Performance'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.type}"

class FacilitatorApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class SalarySubmission(models.Model):
    STATUS_CHOICES = (
        ('pendingCoordination', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    facilitator = models.ForeignKey(User, on_delete=models.CASCADE)
    bank_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.facilitator.username} - {self.status}"

class PaymentSlip(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    slip = models.FileField(upload_to='payment_slips/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class PaymentDetail(models.Model):
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)
    momo_name = models.CharField(max_length=100, blank=True)
    momo_number = PhoneNumberField(blank=True, null=True, help_text="Include country code, e.g., +2341234567890")
    momo_provider = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Payment Details (Updated: {self.updated_at})"

class LiveSession(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    )
    SESSION_TYPE_CHOICES = (
        ('lecture', 'Lecture'),
        ('qna', 'Q&A'),
        ('workshop', 'Workshop'),
        ('other', 'Other'),
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, null=True, blank=True, related_name='live_sessions')
    title = models.CharField(max_length=200)
    zoom_url = models.URLField()
    scheduled_at = models.DateTimeField()
    end_time = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sessions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='lecture')
    is_visible = models.BooleanField(default=True)
    is_open_to_all = models.BooleanField(default=False)  # New field for open sessions

    def __str__(self):
        return f"{self.title} - {self.course.title} ({self.get_status_display()})"

class SessionAttendance(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_attendances')
    joined_at = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} attended {self.session.title}"

class SessionRecap(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recap for {self.session.title}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username}"

class CourseMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='course_materials/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.title}"

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.timestamp}"

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.title}"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Question {self.order} - {self.quiz.title}"

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.text} - {'Correct' if self.is_correct else 'Incorrect'}"

class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    passed = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}"

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()

    def __str__(self):
        return f"{self.title} - {self.course.title}"

class Project(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()

    def __str__(self):
        return f"{self.title} - {self.course.title}"

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    submission_url = models.URLField()
    grade = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.assignment.title if self.assignment else self.project.title}"

class DiscussionPost(models.Model):
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.cohort.name}"

class DiscussionComment(models.Model):
    post = models.ForeignKey(DiscussionPost, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.title}"

class PerformanceRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)
    attendance_score = models.FloatField()
    assignment_score = models.FloatField()
    project_score = models.FloatField()
    total_score = models.FloatField()
    warning_issued = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    reward_earned = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.month}"