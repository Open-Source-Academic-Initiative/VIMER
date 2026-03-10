from django.shortcuts import render, redirect
from django.views import View
from django import forms
from .forms import RegistrationForm

class SignUpView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'identity/signup.html', {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                form.save()
            except forms.ValidationError as exc:
                for field, errors in exc.message_dict.items():
                    for error in errors:
                        form.add_error(field, error)
            else:
                return redirect('login')  # Redirect to the public login page.
        return render(request, 'identity/signup.html', {'form': form})
