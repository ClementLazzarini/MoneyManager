from django.contrib import admin
from .models import Category, Transaction, Owner, MonthlyBudget

admin.site.register(Category)
admin.site.register(Owner)
admin.site.register(Transaction)
admin.site.register(MonthlyBudget)
