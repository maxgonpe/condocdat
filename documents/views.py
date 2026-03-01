from django.shortcuts import render


def dashboard(request):
    """Panel principal del proyecto (raíz)."""
    return render(request, 'dashboard.html')
