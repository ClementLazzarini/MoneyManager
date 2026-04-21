from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Sum
from decimal import Decimal
from .models import Transaction, Owner, Category, MonthlyBudget, DefaultBudget

def dashboard(request, owner_name, year, month):
    owner = get_object_or_404(Owner, name__iexact=owner_name)

    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    # Pour un affichage plus propre en français
    months_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    current_month_name = months_fr[month]
    
    # 1. Inbox : Transactions non traitées
    unprocessed = Transaction.objects.filter(
        owner=owner, is_processed=False,
        bank_date__year=year, bank_date__month=month
    )

    # 2. On récupère TOUTES les catégories pour construire le tableau
    categories = Category.objects.all()
    stats = []

    for cat in categories:
        # 1. On cherche d'abord s'il y a une exception pour CE mois précis
        try:
            budget_obj = MonthlyBudget.objects.get(owner=owner, category=cat, year=year, month=month)
            target_amount = budget_obj.target_amount
        except MonthlyBudget.DoesNotExist:
            # 2. S'il n'y a pas d'exception, on cherche le budget "Classique/Défaut"
            try:
                default_obj = DefaultBudget.objects.get(owner=owner, category=cat)
                target_amount = default_obj.amount
            except DefaultBudget.DoesNotExist:
                # 3. S'il n'y a ni exception ni défaut, l'enveloppe est à 0
                target_amount = 0
        
        # On calcule le coût réel (somme des montants négatifs)
        real_cost = Transaction.objects.filter(
            owner=owner, category=cat, is_processed=True,
            custom_amount__lt=0, # négatif
            custom_date__year=year, custom_date__month=month
        ).aggregate(total=Sum('custom_amount'))['total'] or 0

        # On calcule le gain réel (somme des montants positifs)
        real_gain = Transaction.objects.filter(
            owner=owner, category=cat, is_processed=True,
            custom_amount__gt=0, # positif
            custom_date__year=year, custom_date__month=month
        ).aggregate(total=Sum('custom_amount'))['total'] or 0

        real_cost_abs = abs(real_cost) 
        
        # --- NOUVEAU : Calcul du Delta (Ce qu'il reste dans l'enveloppe) ---
        delta = target_amount - real_cost_abs

        stats.append({
            'category': cat,
            'target': target_amount, # Le prévu
            'real_cost': real_cost_abs, # Le dépensé
            'delta': delta, # Le reste
            'real_gain': real_gain,
        })

    context = {
        'owner': owner,
        'year': year, 
        'month': month,
        'month_name': current_month_name,
        'prev_m': prev_month,
        'prev_y': prev_year,
        'next_m': next_month,
        'next_y': next_year, 
        'unprocessed': unprocessed,
        'stats': stats,
        'categories_list': Category.objects.all(),
    }
    return render(request, 'moneymanager/dashboard.html', context)


def process_transaction(request):
    if request.method == 'POST':
        # 1. On récupère les données envoyées par la modale Alpine
        tx_id = request.POST.get('transaction_id')
        category_id = request.POST.get('category_id')
        custom_amount_str = request.POST.get('custom_amount')
        custom_date = request.POST.get('custom_date')

        # 2. On récupère la transaction et la catégorie en base de données
        transaction = get_object_or_404(Transaction, id=tx_id)
        category = get_object_or_404(Category, id=category_id)
        
        # On convertit le montant en nombre décimal propre
        new_amount = Decimal(custom_amount_str.replace(',', '.'))
        original_amount = transaction.custom_amount

        # 3. LA LOGIQUE DE DIVISION (SPLIT)
        # Si le montant saisi est différent du montant actuel de la ligne
        remainder = original_amount - new_amount
        
        if remainder != 0:
            # On clone la transaction pour le "reste à classer"
            Transaction.objects.create(
                owner=transaction.owner,
                bank_reference=transaction.bank_reference, # On garde la même empreinte
                bank_date=transaction.bank_date,
                bank_label=transaction.bank_label,
                bank_category=transaction.bank_category,
                bank_amount=transaction.bank_amount,
                # Les champs modifiés pour le reste :
                custom_date=transaction.bank_date,
                custom_amount=remainder,
                is_processed=False # Ça retourne dans l'inbox !
            )

        # 4. On met à jour la transaction d'origine
        transaction.category = category
        transaction.custom_amount = new_amount
        transaction.custom_date = custom_date
        transaction.is_processed = True
        transaction.save()

        # 5. On redirige l'utilisateur vers son tableau de bord (au même mois)
        year, month, _ = custom_date.split('-')
        return redirect('moneymanager:dashboard', owner_name=transaction.owner.name.lower(), year=int(year), month=int(month)) # type: ignore
    
