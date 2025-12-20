from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
import random

from apps.courses.models import Lesson
from .models import Quiz, QuizSubmission, EssayQuestionSubmission, Question, QuizQuestionAttempt, Choice
from apps.gamification.models import UserPoints
from apps.gamification.utils import check_badges

class QuizDetailView(LoginRequiredMixin, DetailView):
    model = Quiz
    template_name = 'quiz/quiz_detail.html'

    def get_queryset(self):
        # Ensure user can only view quizzies for courses they are enrolled in
        # Simpler check for now: allow if lesson is accessible
        return Quiz.objects.all() 
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.get_object()
        # Check if user has already submitted
        submission = QuizSubmission.objects.filter(
            student=self.request.user, 
            quiz=quiz
        ).first()
        context['submission'] = submission
        if submission:
            # Get questions from the attempts for this submission
            context['questions'] = Question.objects.filter(question_attempts__submission=submission)
        return context

class QuizStartView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        
        # Check if user has already a submission
        submission, created = QuizSubmission.objects.get_or_create(
            student=request.user, 
            quiz=quiz,
        )

        if not created and submission.end_time:
            messages.info(request, "You have already completed this quiz.")
            return redirect('quiz_detail', pk=pk)

        if created:
            # Select random questions from the bank
            all_questions = list(quiz.question_bank.questions.all())
            random_questions = random.sample(all_questions, min(len(all_questions), quiz.number_of_questions))
            
            # Create attempt objects for each question
            for question in random_questions:
                QuizQuestionAttempt.objects.create(submission=submission, question=question)

            submission.total_questions = len(random_questions)
            submission.save()

        return redirect('quiz_detail', pk=pk)

class QuizTakeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        
        # Check for existing submission
        submission = QuizSubmission.objects.filter(student=request.user, quiz=quiz).first()
        if not submission or submission.end_time:
             messages.error(request, "You have not started this quiz or have already completed it.")
             return redirect('quiz_detail', pk=pk)

        # Calculate score for multiple choice questions
        score = 0
        
        question_attempts = submission.question_attempts.select_related('question').all()

        for attempt in question_attempts:
            question = attempt.question
            answer_key = f'question_{question.id}'

            if question.question_type == 'multiple_choice':
                selected_choice_id = request.POST.get(answer_key)
                if selected_choice_id:
                    try:
                        selected_choice = Choice.objects.get(pk=selected_choice_id, question=question)
                        attempt.selected_choice = selected_choice
                        if selected_choice.is_correct:
                            score += 1
                            attempt.is_correct = True
                        else:
                            attempt.is_correct = False
                    except Choice.DoesNotExist:
                        pass
            elif question.question_type == 'essay':
                answer_text = request.POST.get(answer_key, '').strip()
                if answer_text:
                    attempt.essay_answer = answer_text
            
            attempt.save()
        
        # Update submission
        submission.score = score
        submission.end_time = timezone.now()
        submission.save()

        # Award Points (e.g. 10 points per correct answer)
        points_earned = score * 10
        if points_earned > 0:
            user_points, created = UserPoints.objects.get_or_create(user=request.user)
            user_points.total_points += points_earned
            user_points.save()
            check_badges(request.user)
        
        messages.success(request, f"Quiz submitted! You scored {score}/{submission.total_questions} on multiple choice questions. Essay questions will be graded separately.")
        return redirect('quiz_detail', pk=pk)

class QuizEssaySubmissionsView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        if quiz.course.instructor != request.user:
            messages.error(request, "You are not authorized to view this page.")
            return redirect('quiz_detail', pk=pk)
            
        submissions = QuizQuestionAttempt.objects.filter(submission__quiz=quiz, question__question_type='essay').select_related('submission__student', 'question')
        context = {
            'quiz': quiz,
            'submissions': submissions
        }
        return render(request, 'quiz/essay_submissions.html', context)

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk)
        if quiz.course.instructor != request.user:
            messages.error(request, "You are not authorized to perform this action.")
            return redirect('quiz_detail', pk=pk)

        attempt_id = request.POST.get('attempt_id')
        points = request.POST.get('points')

        attempt = get_object_or_404(QuizQuestionAttempt, pk=attempt_id)
        attempt.points_earned = points # Assuming you add a points_earned field to QuizQuestionAttempt
        attempt.save()
        
        messages.success(request, "Score updated successfully.")
        return redirect('quiz_essay_submissions', pk=pk)
