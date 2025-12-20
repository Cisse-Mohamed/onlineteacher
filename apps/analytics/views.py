from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Avg, Count, Q, OuterRef, Subquery, Max
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import csv
import json
from io import BytesIO

from apps.courses.models import LessonProgress
from apps.courses.models import Course
from apps.quiz.models import QuizSubmission
from .models import StudentPerformanceSnapshot, CourseEngagementMetrics, StudentActivityLog
from .utils import (
    calculate_student_performance,
    create_performance_snapshot,
    calculate_course_engagement,
    get_performance_trends,
    get_student_heatmap_data
)
from apps.forum.models import DiscussionPost


@login_required
def student_performance_dashboard(request, course_id):
    """Student's own performance dashboard"""
    course = get_object_or_404(Course, id=course_id)
    
    # Ensure student is enrolled
    if not course.students.filter(id=request.user.id).exists() and course.instructor != request.user:
        return HttpResponse("Unauthorized", status=403)
    
    # Calculate current metrics
    metrics = calculate_student_performance(request.user, course)
    
    # Get trends (last 30 days)
    trends = get_performance_trends(request.user, course, days=30)
    
    # Recent quiz submissions
    recent_quizzes = QuizSubmission.objects.filter(
        student=request.user,
        quiz__lesson__course=course
    ).order_by('-submitted_at')[:10]
    
    # Lesson completion progress
    total_lessons = course.lessons.count()
    completed_lessons = LessonProgress.objects.filter(
        student=request.user,
        lesson__course=course,
        is_completed=True
    ).count()
    
    context = {
        'course': course,
        'metrics': metrics,
        'trends': trends,
        'recent_quizzes': recent_quizzes,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
    }
    
    return render(request, 'analytics/student_performance.html', context)


@login_required
def instructor_analytics_dashboard(request, course_id):
    """Instructor analytics dashboard for a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Ensure user is the instructor
    if course.instructor != request.user:
        return HttpResponse("Unauthorized", status=403)
    
    # Calculate or get latest engagement metrics
    latest_metrics = CourseEngagementMetrics.objects.filter(course=course).first()
    if not latest_metrics or (timezone.now() - latest_metrics.calculated_at).days > 1:
        # Recalculate if older than 1 day
        latest_metrics = calculate_course_engagement(course)
    
    # Get student heatmap data
    heatmap_data = get_student_heatmap_data(course)
    
    # Get dropout risk students
    at_risk_students = []
    two_weeks_ago = timezone.now() - timedelta(days=14)

    # Subquery to get the last activity timestamp for each student in the course
    last_activity_subquery = StudentActivityLog.objects.filter(
        student=OuterRef('pk'),
        course=course
    ).order_by('-timestamp').values('timestamp')[:1]

    # Annotate students with their last activity date
    students_with_last_activity = course.students.annotate(
        last_activity_timestamp=Subquery(last_activity_subquery)
    )

    for student in students_with_last_activity:
        metrics = calculate_student_performance(student, course)
        has_recent_activity = student.last_activity_timestamp and student.last_activity_timestamp >= two_weeks_ago

        if metrics['completion_rate'] < 20 and not has_recent_activity:
            at_risk_students.append({
                'student': student,
                'metrics': metrics,
                'last_activity': student.last_activity_timestamp
            })
    
    # Activity timeline (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    activity_timeline = StudentActivityLog.objects.filter(
        course=course,
        timestamp__gte=thirty_days_ago
    ).annotate(
        day=TruncDate('timestamp')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    context = {
        'course': course,
        'metrics': latest_metrics,
        'heatmap_data': heatmap_data,
        'at_risk_students': at_risk_students,
        'activity_timeline': list(activity_timeline),
    }
    
    return render(request, 'analytics/instructor_analytics.html', context)


@login_required
def export_student_performance_csv(request, course_id):
    """Export student performance data as CSV"""
    course = get_object_or_404(Course, id=course_id)
    
    # Ensure user is the instructor
    if course.instructor != request.user:
        return HttpResponse("Unauthorized", status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="student_performance_{course.id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Student Name',
        'Username',
        'Email',
        'Quiz Average (%)',
        'Assignment Average',
        'Completion Rate (%)',
        'Engagement Score',
        'Forum Posts',
        'Last Activity'
    ])
    
    # Annotate each student with their forum post count and last activity timestamp
    students = students.annotate(
        forum_post_count=Count('forum_posts', filter=Q(forum_posts__thread__course=course)),
        last_activity_timestamp=Max('activity_logs__timestamp', filter=Q(activity_logs__course=course))
    )

    for student in students:
        metrics = calculate_student_performance(student, course)

        last_activity_str = 'Never'
        if student.last_activity_timestamp:
            # Ensure last_activity_timestamp is timezone-aware if your project uses timezones
            last_activity_ts = student.last_activity_timestamp
            if timezone.is_aware(last_activity_ts):
                last_activity_ts = timezone.localtime(last_activity_ts)
            last_activity_str = last_activity_ts.strftime('%Y-%m-%d %H:%M')

        writer.writerow([
            student.get_full_name() or '',
            student.username,
            student.email,
            metrics['quiz_average'],
            metrics['assignment_average'],
            metrics['completion_rate'],
            metrics['engagement_score'],
            student.forum_post_count,
            last_activity_str
        ])
    
    return response


@login_required
def export_engagement_report_csv(request, course_id):
    """Export course engagement report as CSV"""
    course = get_object_or_404(Course, id=course_id)
    
    if course.instructor != request.user:
        return HttpResponse("Unauthorized", status=403)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="engagement_report_{course.id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Total Students', 'Active Students', 'Avg Completion Rate', 'Avg Quiz Score', 'Forum Activity', 'At Risk'])
    
    metrics_history = CourseEngagementMetrics.objects.filter(course=course).order_by('-calculated_at')[:30]
    
    for metric in metrics_history:
        writer.writerow([
            metric.calculated_at.strftime('%Y-%m-%d'),
            metric.total_students,
            metric.active_students,
            metric.average_completion_rate,
            metric.average_quiz_score,
            metric.forum_activity_count,
            metric.dropout_risk_count
        ])
    
    return response


@login_required
def api_performance_trends(request, course_id):
    """API endpoint for performance trends data"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check authorization
    if not course.students.filter(id=request.user.id).exists() and course.instructor != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    days = int(request.GET.get('days', 30))
    trends = get_performance_trends(request.user, course, days=days)
    
    return JsonResponse(trends)


@login_required
def api_course_engagement(request, course_id):
    """API endpoint for course engagement data"""
    course = get_object_or_404(Course, id=course_id)
    
    if course.instructor != request.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    latest_metrics = CourseEngagementMetrics.objects.filter(course=course).first()
    
    if not latest_metrics:
        latest_metrics = calculate_course_engagement(course)
    
    data = {
        'total_students': latest_metrics.total_students,
        'active_students': latest_metrics.active_students,
        'average_completion_rate': latest_metrics.average_completion_rate,
        'average_quiz_score': latest_metrics.average_quiz_score,
        'forum_activity_count': latest_metrics.forum_activity_count,
        'dropout_risk_count': latest_metrics.dropout_risk_count,
        'calculated_at': latest_metrics.calculated_at.isoformat(),
    }
    
    return JsonResponse(data)