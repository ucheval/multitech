from django.contrib import admin
from .models import (
    Course, Cohort, CourseEnrollment, PaymentSlip, LiveSession, SessionRecap,
    Message, CourseMaterial, Portfolio, Notification, AuditLog, Quiz, Question,
    Answer, QuizAttempt, Assignment, Project, Submission, DiscussionPost,
    DiscussionComment, PerformanceRecord, SalarySubmission, Profile
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'mobile_number', 'country', 'onboarding_quiz_completed')
    search_fields = ('user__username', 'user__email', 'mobile_number', 'country')
    list_filter = ('user_type', 'country', 'onboarding_quiz_completed')

# ... rest of registrations unchanged ...
admin.site.register(Course)
admin.site.register(Cohort)
admin.site.register(CourseEnrollment)
admin.site.register(PaymentSlip)
admin.site.register(LiveSession)
admin.site.register(SessionRecap)
admin.site.register(Message)
admin.site.register(CourseMaterial)
admin.site.register(Portfolio)
admin.site.register(Notification)
admin.site.register(AuditLog)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(QuizAttempt)
admin.site.register(Assignment)
admin.site.register(Project)
admin.site.register(Submission)
admin.site.register(DiscussionPost)
admin.site.register(DiscussionComment)
admin.site.register(PerformanceRecord)
admin.site.register(SalarySubmission)