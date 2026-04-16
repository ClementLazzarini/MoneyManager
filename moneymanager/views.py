from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Sum
from decimal import Decimal
from .models import Transaction, Owner, Category

def dashboard(request, owner_name, year, month):
    owner = get_object_or_404(Owner, name__iexact=owner_name)
    
    # 1. Inbox : Transactions non traitées
    unprocessed = Transaction.objects.filter(
        owner=owner, is_processed=False,
        bank_date__year=year, bank_date__month=month
    )

    # 2. On récupère TOUTES les catégories pour construire le tableau
    categories = Category.objects.all()
    stats = []

    for cat in categories:
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

        stats.append({
            'category': cat,
            'real_cost': abs(real_cost), # On met en positif pour l'affichage
            'real_gain': real_gain,
        })

    context = {
        'owner': owner,
        'year': year, 
        'month': month,
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