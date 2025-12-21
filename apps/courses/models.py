from django.db import models
from django.conf import settings
from django.utils import timezone

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='courses_teaching', blank=True)
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='courses_enrolled', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='course_images/', blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Rich text content")
    video_file = models.FileField(upload_to='lesson_videos/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='lesson_pdfs/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Assignment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    file = models.FileField(upload_to='assignment_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', 'title']

    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submission_files/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('assignment', 'student')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"

class LessonProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'lesson')
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.student.username} - {self.lesson.title} ({'Completed' if self.is_completed else 'In Progress'})"

    def save(self, *args, **kwargs):
        if self.is_completed and self.completed_at is None:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

class PlagiarismReport(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='plagiarism_report')
    score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Plagiarism score (e.g., 0.00 to 100.00)")
    report_url = models.URLField(max_length=500, blank=True, null=True, help_text="URL to the detailed plagiarism report")
    checked_at = models.DateTimeField(auto_now_add=True)
    is_plagiarized = models.BooleanField(default=False, help_text="Flag if the submission is considered plagiarized based on a threshold")

    class Meta:
        ordering = ['-checked_at', 'score']

    def __str__(self):
        return f"Plagiarism Report for {self.submission.assignment.title} by {self.submission.student.username}"
