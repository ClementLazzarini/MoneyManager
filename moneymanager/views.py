from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Sum
from decimal import Decimal
import time
import csv
import hashlib
from datetime import datetime
from .models import Transaction, Owner, Category, MonthlyBudget, DefaultBudget, AccountBalance, GlobalEnvelope, CategoryEnvelopeLink

def index(request):
    """Page d'accueil racine permettant de choisir un propriétaire."""
    owners = Owner.objects.all()
    
    now = datetime.now()
    
    context = {
        'owners': owners,
        'year': now.year,
        'month': now.month,
    }
    return render(request, 'moneymanager/index.html', context)


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
        
        delta = target_amount - real_cost_abs

        link = CategoryEnvelopeLink.objects.filter(owner=owner, category=cat).first()

        stats.append({
            'category': cat,
            'target': target_amount, # Le prévu
            'real_cost': real_cost_abs, # Le dépensé
            'delta': delta, # Le reste
            'real_gain': real_gain,
            'linked_env': link.envelope.name if link else None,
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
        tx_id = request.POST.get('transaction_id')
        category_id = request.POST.get('category_id')
        custom_amount_str = request.POST.get('custom_amount')
        custom_date = request.POST.get('custom_date')

        transaction = get_object_or_404(Transaction, id=tx_id)
        category = get_object_or_404(Category, id=category_id)
        
        new_amount = Decimal(custom_amount_str.replace(',', '.'))
        original_amount = transaction.custom_amount
        remainder = original_amount - new_amount
        
        if remainder != 0:
            Transaction.objects.create(
                owner=transaction.owner,
                bank_reference=transaction.bank_reference,
                bank_date=transaction.bank_date,
                bank_label=transaction.bank_label,
                bank_category=transaction.bank_category,
                bank_amount=transaction.bank_amount,
                custom_date=transaction.bank_date,
                custom_amount=remainder,
                is_processed=False
            )

        transaction.category = category
        transaction.custom_amount = new_amount
        transaction.custom_date = custom_date
        transaction.is_processed = True
        transaction.save()

        link = CategoryEnvelopeLink.objects.filter(owner=transaction.owner, category=category).first()
        
        if link:
            # Si c'est une PROVISION (Épargne), on AJOUTE à l'enveloppe
            if link.link_type == 'PROVISION':
                link.envelope.amount -= new_amount
            # Si c'est une EXPENSE (Dépense), on RETIRE de l'enveloppe
            elif link.link_type == 'EXPENSE':
                link.envelope.amount += new_amount
            link.envelope.save()

        year, month, _ = custom_date.split('-')

        safe_owner_name = transaction.owner.name.lower() if transaction.owner else 'inconnu'

        return redirect('moneymanager:dashboard', owner_name=safe_owner_name, year=int(year), month=int(month))
    
    return redirect('/')
    

def cancel_transaction(request, transaction_id):
    if request.method == 'POST':
        transaction = get_object_or_404(Transaction, id=transaction_id)
        safe_owner_name = transaction.owner.name.lower() if transaction.owner else 'inconnu'
        owner_name = safe_owner_name
        year = transaction.custom_date.year
        month = transaction.custom_date.month
        category_id = transaction.category.pk if transaction.category else None

        # --- ANNULATION DE L'IMPACT SUR L'ENVELOPPE ---
        if transaction.category:
            link = CategoryEnvelopeLink.objects.filter(owner=transaction.owner, category=transaction.category).first()
            if link:
                if link.link_type == 'PROVISION':
                    link.envelope.amount += transaction.custom_amount 
                elif link.link_type == 'EXPENSE':
                    link.envelope.amount -= transaction.custom_amount
                link.envelope.save()

        transaction.is_processed = False
        transaction.category = None
        transaction.save()

        if category_id:
            return redirect('moneymanager:category_detail', owner_name=owner_name, year=year, month=month, category_id=category_id)
            
    return redirect('moneymanager:dashboard')


def category_detail(request, owner_name, year, month, category_id):
    owner = get_object_or_404(Owner, name__iexact=owner_name)
    category = get_object_or_404(Category, id=category_id)

    # On récupère les transactions de cette enveloppe pour ce mois
    transactions = Transaction.objects.filter(
        owner=owner,
        category=category,
        is_processed=True,
        custom_date__year=year,
        custom_date__month=month
    ).order_by('-custom_date') # De la plus récente à la plus ancienne

    context = {
        'owner': owner,
        'year': year,
        'month': month,
        'category': category,
        'transactions': transactions,
    }
    return render(request, 'moneymanager/category_detail.html', context)


def wealth_dashboard(request, owner_name):
    owner = get_object_or_404(Owner, name__iexact=owner_name)

    now = datetime.now()
    
    # 1. Récupération du solde total
    balance_obj, created = AccountBalance.objects.get_or_create(owner=owner)
    total_cash = balance_obj.balance
    
    # 2. Récupération des enveloppes et calcul du total alloué
    envelopes = GlobalEnvelope.objects.filter(owner=owner)
    total_allocated = envelopes.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # 3. Calcul du B/C (Reste à allouer)
    remainder = total_cash - total_allocated
    
    context = {
        'owner': owner,
        'year': now.year,
        'month': now.month,
        'total_cash': total_cash,
        'envelopes': envelopes,
        'total_allocated': total_allocated,
        'remainder': remainder,
    }
    return render(request, 'moneymanager/wealth_dashboard.html', context)


def add_global_envelope(request, owner_name):
    if request.method == 'POST':
        owner = get_object_or_404(Owner, name__iexact=owner_name)
        
        # Récupération des données du formulaire
        name = request.POST.get('name')
        amount = request.POST.get('amount', 0)
        comment = request.POST.get('comment', '')

        # Création de l'enveloppe
        GlobalEnvelope.objects.create(
            owner=owner,
            name=name,
            amount=amount,
            comment=comment
        )
        
        return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)
    
    return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)


def update_account_balance(request, owner_name):
    if request.method == 'POST':
        owner = get_object_or_404(Owner, name__iexact=owner_name)
        new_balance = request.POST.get('balance', 0)
        
        # On récupère l'objet (ou on le crée s'il n'existe pas) et on met à jour
        balance_obj, created = AccountBalance.objects.get_or_create(owner=owner)
        balance_obj.balance = new_balance
        balance_obj.save()
        
        return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)
    
    return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)


def edit_global_envelope(request, owner_name, envelope_id):
    if request.method == 'POST':
        envelope = get_object_or_404(GlobalEnvelope, id=envelope_id, owner__name__iexact=owner_name)
        envelope.name = request.POST.get('name')
        envelope.amount = request.POST.get('amount')
        envelope.comment = request.POST.get('comment')
        envelope.save()
        return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)
    
    return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)


def delete_global_envelope(request, owner_name, envelope_id):
    if request.method == 'POST':
        envelope = get_object_or_404(GlobalEnvelope, id=envelope_id, owner__name__iexact=owner_name)
        envelope.delete()
    return redirect('moneymanager:wealth_dashboard', owner_name=owner_name)


def add_manual_transaction(request, owner_name):
    if request.method == 'POST':
        owner = get_object_or_404(Owner, name__iexact=owner_name)
        
        label = request.POST.get('label')
        amount_str = request.POST.get('amount')
        date_str = request.POST.get('date')
        category_id = request.POST.get('category_id')
        
        amount = Decimal(amount_str.replace(',', '.'))
        
        # On crée une référence unique "MANUAL-..." pour simuler la banque
        unique_ref = f"MANUAL-{int(time.time())}"
        
        # 1. Création de la transaction
        transaction = Transaction.objects.create(
            owner=owner,
            bank_reference=unique_ref,
            bank_date=date_str,
            bank_label=f"[MANUEL] {label}",
            bank_amount=amount,
            custom_date=date_str,
            custom_amount=amount,
            is_processed=False
        )
        
        # 2. Si une catégorie a été choisie, on la classe et on active le pont
        if category_id:
            category = get_object_or_404(Category, id=category_id)
            transaction.category = category
            transaction.is_processed = True
            transaction.save()
            
            link = CategoryEnvelopeLink.objects.filter(owner=owner, category=category).first()
            if link:
                if link.link_type == 'PROVISION':
                    link.envelope.amount -= amount 
                elif link.link_type == 'EXPENSE':
                    link.envelope.amount += amount
                link.envelope.save()
                
        # 3. Redirection vers le mois de la dépense
        year, month, _ = date_str.split('-')
        return redirect('moneymanager:dashboard', owner_name=owner_name, year=int(year), month=int(month))
        
    return redirect('moneymanager:dashboard', owner_name=owner_name, year=datetime.now().year, month=datetime.now().month)


def import_page(request, owner_name):
    """Affiche la page d'importation"""
    owner = get_object_or_404(Owner, name__iexact=owner_name)
    now = datetime.now()
    
    context = {
        'owner': owner,
        'year': now.year,
        'month': now.month,
    }
    return render(request, 'moneymanager/import.html', context)

def import_csv_action(request, owner_name):
    """Traite le fichier CSV uploadé"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        owner = get_object_or_404(Owner, name__iexact=owner_name)
        csv_file = request.FILES['csv_file']
        
        # Lecture du fichier
        try:
            decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        except UnicodeDecodeError:
            csv_file.seek(0)
            decoded_file = csv_file.read().decode('latin-1').splitlines()
            
        reader = csv.DictReader(decoded_file, delimiter=';')
        
        count_added = 0
        for row in reader:
            date_str = row.get('dateOp')
            label = row.get('label', '')
            amount_raw = row.get('amount', '0')
            
            if not date_str or not amount_raw:
                continue

            # Nettoyage du montant (Bourso utilise la virgule et des espaces)
            amount_str = amount_raw.replace(',', '.').replace(' ', '')
            amount = Decimal(amount_str)

            # Calcul du hash unique (identique à ton script import_csv.py)
            unique_string = f"{date_str}_{label}_{amount}"
            bank_ref = hashlib.md5(unique_string.encode('utf-8')).hexdigest()

            # Création si n'existe pas
            if not Transaction.objects.filter(bank_reference=bank_ref).exists():
                Transaction.objects.create(
                    owner=owner,
                    bank_reference=bank_ref,
                    bank_date=date_str,
                    bank_label=label[:255],
                    bank_category=row.get('category', '')[:100],
                    bank_amount=amount,
                    custom_date=date_str,
                    custom_amount=amount,
                    is_processed=False
                )
                count_added += 1
                
        # Redirection vers le dashboard avec un petit message de succès par exemple
        now = datetime.now()
        return redirect('moneymanager:dashboard', owner_name=owner.name.lower(), year=now.year, month=now.month)
    
    return redirect('moneymanager:import_page', owner_name=owner_name)
