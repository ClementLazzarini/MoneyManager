from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'moneymanager'

urlpatterns = [
    path('', views.index, name='index'),

    # --- AUTHENTIFICATION ---
    path('login/', auth_views.LoginView.as_view(template_name='moneymanager/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # DASHBOARD
    path('dashboard/<int:year>/<int:month>/', views.dashboard, name='dashboard'),
    path('dashboard/<int:year>/<int:month>/category/<int:category_id>/', views.category_detail, name='category_detail'),

    # Transactions
    path('process-transaction/', views.process_transaction, name='process_transaction'),
    path('cancel-transaction/<int:transaction_id>/', views.cancel_transaction, name='cancel_transaction'),
    path('add-manual-transaction/', views.add_manual_transaction, name='add_manual_transaction'),

    # Wealth Management
    path('wealth/', views.wealth_dashboard, name='wealth_dashboard'),
    path('wealth/add-envelope/', views.add_global_envelope, name='add_global_envelope'),
    path('wealth/update-balance/', views.update_account_balance, name='update_account_balance'),
    path('wealth/edit-envelope/<int:envelope_id>/', views.edit_global_envelope, name='edit_global_envelope'),
    path('wealth/delete-envelope/<int:envelope_id>/', views.delete_global_envelope, name='delete_global_envelope'),

    # CSV Import
    path('import/', views.import_page, name='import_page'),
    path('import-action/', views.import_csv_action, name='import_csv_action'),

    # Paramètres & Configuration
    path('settings/', views.settings_page, name='settings_page'),
    path('settings/add-category/', views.add_category, name='add_category'),
    path('settings/add-rule/', views.add_auto_rule, name='add_auto_rule'),

]