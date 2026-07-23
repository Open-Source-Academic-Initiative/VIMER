from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.shortcuts import render
from django.utils import timezone

from apps.corporate.models import Organization
from apps.evaluation.models import ApplicationCriterionEvaluation, AwardDecision
from apps.identity.models import User
from apps.marketplace.models import Application, Challenge


@staff_member_required
def platform_dashboard(request):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    awarded_duration = ExpressionWrapper(
        F("decided_at") - F("challenge__created_at"),
        output_field=DurationField(),
    )
    mean_award_duration = (
        AwardDecision.objects.annotate(duration=awarded_duration)
        .aggregate(mean=Avg("duration"))
        .get("mean")
    )
    context = {
        "organization_count": Organization.objects.count(),
        "active_representative_count": User.objects.operational().count(),
        "challenge_counts": Challenge.objects.values("status").annotate(count=Count("id")),
        "submitted_application_count": Application.objects.submitted().count(),
        "mean_award_duration": mean_award_duration,
        "recent_evaluation_count": ApplicationCriterionEvaluation.objects.filter(
            evaluated_at__gte=thirty_days_ago
        ).count(),
    }
    return render(request, "admin/platform_dashboard.html", context)
