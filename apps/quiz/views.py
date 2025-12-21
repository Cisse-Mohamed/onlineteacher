from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
import random
from django.db import transaction

from apps.courses.models import Lesson
from .models import Quiz, QuizSubmission, Question, QuizQuestionAttempt
from .forms import QuizTakeForm, EssayGradeForm
from apps.gamification.models import UserPoints
from apps.gamification.utils import check_badges

class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = 'quiz/quiz_detail.html'

    def get_queryset(self):
        # Optimize by prefetching related data that will be used.
        return Quiz.objects.select_related('course').all() 
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.get_object()
        
        # Get the user's submission for this quiz
        submission = QuizSubmission.objects.filter(
            student=self.request.user, 
            quiz=quiz
        ).prefetch_related(
            'question_attempts__question__choices' # prefetch all related data
        ).first()

        context['submission'] = submission
        if submission:
            question_attempts = submission.question_attempts.select_related('question').all()
            context['form'] = QuizTakeForm(question_attempts=question_attempts)
        return context

class QuizStartView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz.objects.select_related('question_bank'), pk=pk)
        
        submission, created = QuizSubmission.objects.get_or_create(
            student=request.user, 
            quiz=quiz,
            defaults={'start_time': timezone.now()}
        )

        if not created and submission.end_time:
            messages.info(request, "You have already completed this quiz.")
            return redirect('quiz:quiz_detail', pk=pk)

        # If the submission was just created, populate it with questions.
        if submission.question_attempts.count() == 0:
            with transaction.atomic():
                all_questions = list(quiz.question_bank.questions.all())
                num_questions = min(len(all_questions), quiz.number_of_questions)
                random_questions = random.sample(all_questions, num_questions)
                
                for question in random_questions:
                    QuizQuestionAttempt.objects.create(submission=submission, question=question)

                submission.total_questions = num_questions
                submission.save()

        return redirect('quiz:quiz_detail', pk=pk)

class QuizTakeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        submission = get_object_or_404(QuizSubmission, student=request.user, quiz=quiz)

        if submission.end_time:
             messages.error(request, "You have already completed this quiz.")
             return redirect('quiz:quiz_detail', pk=pk)

        question_attempts = submission.question_attempts.select_related('question').all()
        form = QuizTakeForm(request.POST, question_attempts=question_attempts)
        if form.is_valid():
            score = form.save(submission=submission, question_attempts=question_attempts)
            submission.mcq_score = score
            submission.total_score += score # Add MCQ score to total
            submission.end_time = timezone.now() # Mark as completed
            submission.save()

            # Award Points
            points_earned = score * quiz.points_per_question
            if points_earned > 0:
                user_points, _ = UserPoints.objects.get_or_create(user=request.user)
                user_points.total_points += points_earned
                user_points.save()
                check_badges(request.user)
            
            messages.success(request, f"Quiz submitted! You scored {score}/{submission.total_questions} on multiple choice questions. Essay questions will be graded separately.")
        else:
            messages.error(request, "There was an error with your submission. Please check your answers.")

        return redirect('quiz:quiz_detail', pk=pk)

class QuizEssaySubmissionsView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz.objects.select_related('course'), pk=pk)
        if not request.user.is_instructor or request.user not in quiz.course.instructors.all():
            return redirect('quiz:quiz_detail', pk=pk)
            
        attempts = QuizQuestionAttempt.objects.filter(
            submission__quiz=quiz, 
            question__question_type='essay'
        ).select_related('submission__student', 'question')

        # Create a form instance for each attempt to allow inline grading
        forms = {attempt.id: EssayGradeForm(instance=attempt, prefix=f'attempt_{attempt.id}') for attempt in attempts}

        context = {
            'quiz': quiz,
            'attempts_with_forms': [(attempt, forms[attempt.id]) for attempt in attempts]
        }
        return render(request, 'quiz/essay_submissions.html', context)

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz.objects.select_related('course'), pk=pk)
        if not request.user.is_instructor or request.user not in quiz.course.instructors.all():
            messages.error(request, "You are not authorized to perform this action.")
            return redirect('quiz:quiz_detail', pk=pk)

        attempt_id = request.POST.get('attempt_id')
        if not attempt_id:
            messages.error(request, "Invalid request.")
            return redirect('quiz:quiz_essay_submissions', pk=pk)

        attempt = get_object_or_404(QuizQuestionAttempt, pk=attempt_id)
        form = EssayGradeForm(request.POST, instance=attempt, prefix=f'attempt_{attempt.id}')

        if form.is_valid():
            form.save()
            # Update the total score of the submission
            submission = attempt.submission
            submission.total_score += attempt.points_earned
            submission.save()
            messages.success(request, f"Score updated for {attempt.submission.student.username}'s essay.")
        else:
            messages.error(request, "Invalid score submitted.")

        return redirect('quiz:quiz_essay_submissions', pk=pk)
