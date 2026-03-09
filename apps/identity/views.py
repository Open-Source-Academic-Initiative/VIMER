from django.shortcuts import render, redirect
from django.views import View
from .forms import RegistrationForm

class SignUpView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'identity/signup.html', {'form': form})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login') # Redirigir al login público
        return render(request, 'identity/signup.html', {'form': form})
