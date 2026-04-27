from django.urls import path
from . import views

app_name = 'moneymanager'

urlpatterns = [
    # DASHBOARD
    path('dashboard/<str:owner_name>/<int:year>/<int:month>/', views.dashboard, name='dashboard'),
    path('dashboard/<str:owner_name>/<int:year>/<int:month>/category/<int:category_id>/', views.category_detail, name='category_detail'),

    # Transactions
    path('process-transaction/', views.process_transaction, name='process_transaction'),
    path('cancel-transaction/<int:transaction_id>/', views.cancel_transaction, name='cancel_transaction'),
    path('add-manual-transaction/<str:owner_name>/', views.add_manual_transaction, name='add_manual_transaction'),

    # Wealth Management
    path('wealth/<str:owner_name>/', views.wealth_dashboard, name='wealth_dashboard'),
    path('wealth/<str:owner_name>/add-envelope/', views.add_global_envelope, name='add_global_envelope'),
    path('wealth/<str:owner_name>/update-balance/', views.update_account_balance, name='update_account_balance'),
    path('wealth/<str:owner_name>/edit-envelope/<int:envelope_id>/', views.edit_global_envelope, name='edit_global_envelope'),
    path('wealth/<str:owner_name>/delete-envelope/<int:envelope_id>/', views.delete_global_envelope, name='delete_global_envelope'),

    # CSV Import
    path('import/<str:owner_name>/', views.import_page, name='import_page'),
    path('import-action/<str:owner_name>/', views.import_csv_action, name='import_csv_action'),

]