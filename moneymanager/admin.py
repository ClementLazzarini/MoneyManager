from django.contrib import admin
from .models import Category, Transaction, Owner, MonthlyBudget, DefaultBudget, AccountBalance, GlobalEnvelope, CategoryEnvelopeLink, AutoCategoryRule

# --- PERSONNALISATION DE L'INTERFACE GLOBALE ---
admin.site.site_header = "Administration MoneyManager"
admin.site.site_title = "MoneyManager Admin"
admin.site.index_title = "Gestion du Coffre-Fort"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # Les colonnes visibles dans le tableau
    list_display = ('bank_date', 'owner', 'bank_label', 'custom_amount', 'category', 'is_processed')
    
    # Les filtres sur le côté droit (Indispensable pour débusquer tes doublons !)
    list_filter = ('is_processed', 'owner', 'bank_date', 'category')
    
    # Barre de recherche 
    search_fields = ('bank_label', 'bank_reference', 'custom_amount')
    
    # Tri par défaut (du plus récent au plus ancien)
    ordering = ('-bank_date',)
    
    # Rendre certaines colonnes modifiables directement sans ouvrir la transaction
    list_editable = ('category', 'is_processed')
    
    # Pagination pour ne pas surcharger la page
    list_per_page = 50


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('icon', 'name', 'color_code')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user')


@admin.register(MonthlyBudget)
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ('owner', 'category', 'month', 'year', 'target_amount')
    list_filter = ('year', 'month', 'owner', 'category')
    list_editable = ('target_amount',)


@admin.register(DefaultBudget)
class DefaultBudgetAdmin(admin.ModelAdmin):
    list_display = ('owner', 'category', 'amount')
    list_filter = ('owner', 'category')
    list_editable = ('amount',)


@admin.register(GlobalEnvelope)
class GlobalEnvelopeAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'amount')
    list_filter = ('owner',)
    search_fields = ('name', 'comment')
    list_editable = ('amount',)


@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    list_display = ('owner', 'balance')


@admin.register(CategoryEnvelopeLink)
class CategoryEnvelopeLinkAdmin(admin.ModelAdmin):
    list_display = ('owner', 'category', 'envelope', 'link_type')
    list_filter = ('owner', 'link_type', 'envelope')


@admin.register(AutoCategoryRule)
class AutoCategoryRuleAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'category', 'owner')
    list_filter = ('owner', 'category')
    search_fields = ('keyword',)
    list_editable = ('category',)