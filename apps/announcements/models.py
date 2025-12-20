from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.courses.models import Course

User = get_user_model()


class Announcement(models.Model):
    SCOPE_CHOICES = [
        ('platform', 'Platform-wide'),
        ('course', 'Course-specific'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements')
    
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default='course')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='announcements', null=True, blank=True, 
                               help_text="Required if scope is 'course'")
    
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    send_email = models.BooleanField(default=True, help_text="Send email notification to recipients")
    is_pinned = models.BooleanField(default=False, help_text="Pin announcement to top")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['scope', 'course']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_recipients(self):
        """Get list of users who should receive this announcement"""
        if self.scope == 'platform':
            return User.objects.all()
        elif self.scope == 'course' and self.course:
            # Course students + instructor
            recipients = list(self.course.students.all())
            recipients.append(self.course.instructor)
            return recipients
        return []


class AnnouncementRead(models.Model):
    """Track which users have read which announcements"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcement_reads')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('announcement', 'user')
        indexes = [
            models.Index(fields=['user', '-read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} read {self.announcement.title}"