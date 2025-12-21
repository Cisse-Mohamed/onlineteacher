from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from .models import PeerReviewAssignment, PeerReviewSubmission, PeerReviewReview

class PeerReviewAssignmentDetailView(LoginRequiredMixin, DetailView):
    model = PeerReviewAssignment
    template_name = 'peer_review/assignment_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = self.get_object()
        student = self.request.user

        # Get the student's submission
        submission = PeerReviewSubmission.objects.filter(assignment=assignment, student=student).first()
        context['submission'] = submission

        # If submission exists, get reviews for it
        if submission:
            context['reviews_received'] = submission.reviews.all()

        # Get submissions for the current student to review
        # For simplicity, we'll assign one submission to review that is not the student's own
        # A more robust system would have a more complex assignment algorithm
        context['submission_to_review'] = PeerReviewSubmission.objects.filter(
            assignment=assignment
        ).exclude(student=student).exclude(reviews__reviewer=student).first()

        return context

class PeerReviewSubmissionCreateView(LoginRequiredMixin, CreateView):
    model = PeerReviewSubmission
    fields = ['submission_file']
    template_name = 'peer_review/assignment_detail.html' # Re-uses the detail template for the form

    def form_valid(self, form):
        assignment = get_object_or_404(PeerReviewAssignment, pk=self.kwargs['assignment_pk'])
        form.instance.assignment = assignment
        form.instance.student = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('peer_review:assignment_detail', kwargs={'pk': self.kwargs['assignment_pk']})

class PeerReviewReviewCreateView(LoginRequiredMixin, CreateView):
    model = PeerReviewReview
    fields = ['score', 'comments']
    template_name = 'peer_review/assignment_detail.html' # Re-uses the detail template

    def form_valid(self, form):
        submission = get_object_or_404(PeerReviewSubmission, pk=self.kwargs['submission_pk'])
        form.instance.submission = submission
        form.instance.reviewer = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        submission = self.object.submission
        return reverse('peer_review:assignment_detail', kwargs={'pk': submission.assignment.pk})

class PeerReviewAssignmentCreateView(LoginRequiredMixin, CreateView):
    model = PeerReviewAssignment
    fields = ['title', 'description', 'due_date']
    template_name = 'peer_review/assignment_create.html'

    def form_valid(self, form):
        from apps.courses.models import Lesson
        lesson = get_object_or_404(Lesson, pk=self.kwargs['lesson_pk'])
        form.instance.lesson = lesson
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:lesson_detail', kwargs={'course_id': self.object.lesson.course.pk, 'lesson_id': self.object.lesson.pk})


