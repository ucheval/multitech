from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Cohort, Submission, PerformanceRecord, Notification
from datetime import timedelta

class Command(BaseCommand):
    help = 'Calculates monthly performance scores'

    def handle(self, *args, **options):
        cohorts = Cohort.objects.all()
        current_month = 1  # Adjust based on program timeline
        for cohort in cohorts:
            for student in cohort.students.all():
                attendance_score = 0  # Placeholder: Calculate based on LiveSession attendance
                assignment_submissions = Submission.objects.filter(
                    user=student,
                    assignment__course__cohort=cohort,
                    submitted_at__gte=timezone.now() - timedelta(days=30)
                )
                project_submissions = Submission.objects.filter(
                    user=student,
                    project__course__cohort=cohort,
                    submitted_at__gte=timezone.now() - timedelta(days=30)
                )
                assignment_score = sum(s.grade for s in assignment_submissions if s.grade) / 100 * 10 if assignment_submissions else 0
                project_score = sum(s.grade for s in project_submissions if s.grade) / 100 * 5 if project_submissions else 0
                total_score = attendance_score + assignment_score + project_score

                record, created = PerformanceRecord.objects.get_or_create(
                    user=student,
                    cohort=cohort,
                    month=current_month,
                    defaults={
                        'attendance_score': attendance_score,
                        'assignment_score': assignment_score,
                        'project_score': project_score,
                        'total_score': total_score
                    }
                )
                if total_score < 25 and current_month == 1 and not record.warning_issued:
                    record.warning_issued = True
                    record.save()
                    Notification.objects.create(
                        user=student,
                        type='performance',
                        message="Warning: Your Month 1 performance is below 25%."
                    )
                elif total_score < 50 and current_month == 2 and not record.suspended:
                    record.suspended = True
                    record.save()
                    Notification.objects.create(
                        user=student,
                        type='performance',
                        message="You have been suspended due to low performance in Month 2."
                    )
        self.stdout.write(self.style.SUCCESS('Performance scores calculated'))