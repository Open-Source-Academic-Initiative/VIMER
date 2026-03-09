from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy
from .models import Challenge, Application

class RoleRequiredMixin(UserPassesTestMixin):
    role_required = None
    
    def test_func(self):
        return (
            self.request.user.is_authenticated and 
            self.request.user.organization and 
            self.request.user.organization.role == self.role_required
        )

class ChallengeListView(LoginRequiredMixin, ListView):
    model = Challenge
    template_name = 'marketplace/challenge_list.html'
    context_object_name = 'challenges'

class ChallengeDetailView(LoginRequiredMixin, DetailView):
    model = Challenge
    template_name = 'marketplace/challenge_detail.html'
    context_object_name = 'challenge'

class ChallengeCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Challenge
    role_required = 'DEMANDANTE'
    fields = ['title', 'description']
    template_name = 'marketplace/challenge_form.html'
    success_url = reverse_lazy('marketplace:challenge-list')

    def form_valid(self, form):
        form.instance.publisher = self.request.user.organization
        return super().form_valid(form)

class ApplicationCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Application
    role_required = 'OFERENTE'
    fields = ['proposal_text']
    template_name = 'marketplace/application_form.html'
    success_url = reverse_lazy('marketplace:challenge-list')

    def form_valid(self, form):
        challenge = Challenge.objects.get(pk=self.kwargs['pk'])
        form.instance.challenge = challenge
        form.instance.applicant = self.request.user.organization
        return super().form_valid(form)
