"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

app_name = 'moneymanager'

urlpatterns = [
    path('dashboard/<str:owner_name>/<int:year>/<int:month>/', views.dashboard, name='dashboard'),
    path('process-transaction/', views.process_transaction, name='process_transaction'),
    path('dashboard/<str:owner_name>/<int:year>/<int:month>/category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('cancel-transaction/<int:transaction_id>/', views.cancel_transaction, name='cancel_transaction'),
    path('wealth/<str:owner_name>/', views.wealth_dashboard, name='wealth_dashboard'),
    path('wealth/<str:owner_name>/add-envelope/', views.add_global_envelope, name='add_global_envelope'),
    path('wealth/<str:owner_name>/update-balance/', views.update_account_balance, name='update_account_balance'),
    path('wealth/<str:owner_name>/edit-envelope/<int:envelope_id>/', views.edit_global_envelope, name='edit_global_envelope'),
    path('wealth/<str:owner_name>/delete-envelope/<int:envelope_id>/', views.delete_global_envelope, name='delete_global_envelope'),
]