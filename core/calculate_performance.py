from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Cohort, Submission, PerformanceRecord, Notification
from datetime import timedelta


class Command(BaseCommand):
    help = 'Calculates monthly performance scores for all cohort students'

    def handle(self, *args, **options):
        cohorts = Cohort.objects.prefetch_related('students').all()
        current_month = timezone.now().strftime('%Y-%m')  # e.g. "2025-06" — human-readable

        for cohort in cohorts:
            for student in cohort.students.all():

                # --- Attendance (placeholder until SessionAttendance scoring is built) ---
                attendance_score = 0

                # --- Assignments submitted in last 30 days ---
                assignment_submissions = Submission.objects.filter(
                    user=student,
                    assignment__isnull=False,
                    assignment__course=cohort.course,
                    submitted_at__gte=timezone.now() - timedelta(days=30)
                )
                # --- Projects submitted in last 30 days ---
                project_submissions = Submission.objects.filter(
                    user=student,
                    project__isnull=False,
                    project__course=cohort.course,
                    submitted_at__gte=timezone.now() - timedelta(days=30)
                )

                assignment_score = (
                    sum(s.grade for s in assignment_submissions if s.grade is not None)
                    / 100 * 10
                    if assignment_submissions.exists() else 0
                )
                project_score = (
                    sum(s.grade for s in project_submissions if s.grade is not None)
                    / 100 * 5
                    if project_submissions.exists() else 0
                )
                total_score = attendance_score + assignment_score + project_score

                # PerformanceRecord has no cohort field — use user + month as the key
                record, created = PerformanceRecord.objects.get_or_create(
                    user=student,
                    month=current_month,
                    defaults={
                        'attendance_score': attendance_score,
                        'assignment_score': assignment_score,
                        'project_score': project_score,
                        'total_score': total_score,
                    }
                )

                if not created:
                    # Update scores if record already exists this month
                    record.attendance_score = attendance_score
                    record.assignment_score = assignment_score
                    record.project_score = project_score
                    record.total_score = total_score
                    record.save()

                # --- Performance warnings / suspensions ---
                month_number = self._month_number(cohort, student)

                if total_score < 25 and month_number == 1 and not record.warning_issued:
                    record.warning_issued = True
                    record.save()
                    Notification.objects.create(
                        user=student,
                        type='performance',
                        message='Warning: Your Month 1 performance is below 25%. Please improve attendance and submissions.'
                    )

                elif total_score < 50 and month_number == 2 and not record.suspended:
                    record.suspended = True
                    record.save()
                    Notification.objects.create(
                        user=student,
                        type='performance',
                        message='You have been suspended due to low performance in Month 2. Please contact your facilitator.'
                    )

        self.stdout.write(self.style.SUCCESS('Performance scores calculated successfully.'))

    def _month_number(self, cohort, student):
        """
        Returns which program month the student is in (1, 2, 3…).
        Based on how many PerformanceRecord rows exist for this student.
        Adjust this logic once you have a program start_date on Cohort.
        """
        return PerformanceRecord.objects.filter(user=student).count()