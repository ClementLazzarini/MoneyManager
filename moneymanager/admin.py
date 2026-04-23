from django.contrib import admin
from .models import Category, Transaction, Owner, MonthlyBudget, DefaultBudget, AccountBalance, GlobalEnvelope, CategoryEnvelopeLink

admin.site.register(Category)
admin.site.register(Owner)
admin.site.register(Transaction)
admin.site.register(MonthlyBudget)
admin.site.register(DefaultBudget)
admin.site.register(AccountBalance)
admin.site.register(GlobalEnvelope)
admin.site.register(CategoryEnvelopeLink)
