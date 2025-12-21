from django.db import models
from django.conf import settings

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.SlugField(unique=True)
    icon = models.ImageField(upload_to='badges/', blank=True, null=True)
    points_required = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-points_required', 'name']

class UserPoints(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gamification_points')
    total_points = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_points']

    def __str__(self):
        return f"{self.user.username} - {self.total_points} pts"

class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_to')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-awarded_at']

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

class DailyChallenge(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('once', 'Once'), # for challenges that can only be completed once ever
    ]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    points_award = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, max_length=200)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='daily')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-points_award', 'name']

    def __str__(self):
        return self.name

class UserDailyChallenge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_challenges_completed')
    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, related_name='user_completions')
    completed_date = models.DateField(auto_now_add=True) # Automatically set to today's date
    is_completed = models.BooleanField(default=True) # Will always be true if an entry exists

    class Meta:
        # A user can only complete a daily challenge once per day
        unique_together = ('user', 'challenge', 'completed_date')
        ordering = ['-completed_date']

    def __str__(self):
        return f"{self.user.username} completed {self.challenge.name} on {self.completed_date}"
