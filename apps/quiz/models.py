from django.db import models
from django.conf import settings
from apps.courses.models import Course

class QuestionBank(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='question_banks')
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    question_bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(help_text="Duration of the quiz in minutes", default=0)
    number_of_questions = models.PositiveIntegerField(help_text="Number of questions to be drawn from the bank")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('essay', 'Essay'),
    ]
    question_bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')

    def __str__(self):
        return self.text[:50]

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class QuizSubmission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_submissions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')

    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField()
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"

class QuizQuestionAttempt(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='question_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True) # For MCQs
    essay_answer = models.TextField(blank=True, null=True) # For essay questions
    is_correct = models.BooleanField(null=True, blank=True) # Null for essays until graded
    points_earned = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('submission', 'question')

    def __str__(self):
        return f"{self.submission.student.username}'s attempt on {self.question.text[:50]}"


class EssayQuestionSubmission(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='essay_submissions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='essay_submissions')
    answer = models.TextField()
    ai_feedback = models.TextField(blank=True, null=True)
    ai_score = models.PositiveIntegerField(null=True, blank=True)
    instructor_score = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Essay submission for {self.question.text[:50]} by {self.submission.student.username}"
