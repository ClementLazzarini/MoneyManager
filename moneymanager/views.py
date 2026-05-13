from django.shortcuts import redirect, render, get_object_or_404
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
import time
import csv
import hashlib
from datetime import datetime
from .models import Transaction, Category, MonthlyBudget, DefaultBudget, AccountBalance, GlobalEnvelope, CategoryEnvelopeLink, AutoCategoryRule

def index(request):
    """Page d'accueil : Affiche le portail avec le bon contexte."""
    now = datetime.now()
    context = {
        'year': now.year,
        'month': now.month,
    }
    
    if request.user.is_authenticated:
        if hasattr(request.user, 'owner_profile'):
            context['owner'] = request.user.owner_profile
            
    return render(request, 'moneymanager/index.html', context)


@login_required
def dashboard(request, year, month):
    owner = request.user.owner_profile

    # --- 1. GESTION DES DATES ---
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year

    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year

    months_fr = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    current_month_name = months_fr[month]
    
    # --- 2. RÉCUPÉRATION DES TRANSACTIONS ---
    # Inbox : On regarde la date de BANQUE
    unprocessed = Transaction.objects.filter(
        owner=owner, is_processed=False,
        bank_date__year=year, bank_date__month=month
    )

    # Totaux : On regarde la date PERSONNALISÉE (ton choix de budget)
    processed_tx = Transaction.objects.filter(
        owner=owner, is_processed=True,
        custom_date__year=year, custom_date__month=month
    )

    # --- 3. CALCUL DES CATÉGORIES ---
    categories = Category.objects.all()
    stats = []

    for cat in categories:
        # Budget (Exception mensuelle ou défaut)
        budget_obj = MonthlyBudget.objects.filter(owner=owner, category=cat, year=year, month=month).first()
        if budget_obj:
            target_amount = budget_obj.target_amount
        else:
            default_obj = DefaultBudget.objects.filter(owner=owner, category=cat).first()
            target_amount = default_obj.amount if default_obj else 0
        
        # On filtre les transactions traitées du mois pour cette catégorie
        cat_tx = processed_tx.filter(category=cat)
        
        real_cost = abs(cat_tx.filter(custom_amount__lt=0).aggregate(Sum('custom_amount'))['custom_amount__sum'] or 0)
        real_gain = cat_tx.filter(custom_amount__gt=0).aggregate(Sum('custom_amount'))['custom_amount__sum'] or 0
        
        delta = target_amount - real_cost
        link = CategoryEnvelopeLink.objects.filter(owner=owner, category=cat).first()

        stats.append({
            'category': cat,
            'target': target_amount,
            'real_cost': real_cost,
            'delta': delta,
            'real_gain': real_gain,
            'linked_env': link.envelope.name if link else None,
        })

    # --- 4. CALCULS DU RÉCAPITULATIF GLOBAL ---
    total_income = processed_tx.filter(custom_amount__gt=0).aggregate(Sum('custom_amount'))['custom_amount__sum'] or Decimal('0.00')
    total_expenses_raw = processed_tx.filter(custom_amount__lt=0).aggregate(Sum('custom_amount'))['custom_amount__sum'] or Decimal('0.00')
    
    total_expenses = abs(total_expenses_raw)
    savings_capacity = total_income - total_expenses

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
        'total_income': total_income,
        'total_expenses': total_expenses,
        'savings_capacity': savings_capacity,
        'categories_list': categories,
    }
    return render(request, 'moneymanager/dashboard.html', context)


@login_required
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

        messages.success(request, "Opération classée avec succès !")

        return redirect('moneymanager:dashboard', year=int(year), month=int(month))
    
    return redirect('/')
    

@login_required
def cancel_transaction(request, transaction_id):
    if request.method == 'POST':
        transaction = get_object_or_404(Transaction, id=transaction_id)
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
            return redirect('moneymanager:category_detail', year=year, month=month, category_id=category_id)
    
    now = datetime.now()
            
    return redirect('moneymanager:dashboard', year=now.year, month=now.month)


@login_required
def category_detail(request, year, month, category_id):
    owner = request.user.owner_profile
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


@login_required
def wealth_dashboard(request):
    owner = request.user.owner_profile

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


@login_required
def add_global_envelope(request):
    if request.method == 'POST':
        owner = request.user.owner_profile
        
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
        
        return redirect('moneymanager:wealth_dashboard')
    
    return redirect('moneymanager:wealth_dashboard')


@login_required
def update_account_balance(request):
    if request.method == 'POST':
        owner = request.user.owner_profile
        new_balance = request.POST.get('balance', 0)
        
        # On récupère l'objet (ou on le crée s'il n'existe pas) et on met à jour
        balance_obj, created = AccountBalance.objects.get_or_create(owner=owner)
        balance_obj.balance = new_balance
        balance_obj.save()
        
        return redirect('moneymanager:wealth_dashboard')
    
    return redirect('moneymanager:wealth_dashboard')


@login_required
def edit_global_envelope(request, envelope_id):
    if request.method == 'POST':
        owner = request.user.owner_profile
        envelope = get_object_or_404(GlobalEnvelope, id=envelope_id, owner=owner)
        envelope.name = request.POST.get('name')
        envelope.amount = request.POST.get('amount')
        envelope.comment = request.POST.get('comment')
        envelope.save()
        return redirect('moneymanager:wealth_dashboard')
    
    return redirect('moneymanager:wealth_dashboard')


@login_required
def delete_global_envelope(request, envelope_id):
    if request.method == 'POST':
        owner = request.user.owner_profile
        envelope = get_object_or_404(GlobalEnvelope, id=envelope_id, owner=owner)
        envelope.delete()
    return redirect('moneymanager:wealth_dashboard')


@login_required
def add_manual_transaction(request):
    if request.method == 'POST':
        owner = request.user.owner_profile
        
        label = request.POST.get('label')
        amount_str = request.POST.get('amount')
        date_str = request.POST.get('date')
        category_id = request.POST.get('category_id')
        
        amount = Decimal(amount_str.replace(',', '.'))
        
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
        return redirect('moneymanager:dashboard', year=int(year), month=int(month))
        
    return redirect('moneymanager:dashboard', year=datetime.now().year, month=datetime.now().month)


@login_required
def import_page(request):
    """Affiche la page d'importation"""
    owner = request.user.owner_profile
    now = datetime.now()
    
    context = {
        'owner': owner,
        'year': now.year,
        'month': now.month,
    }
    return render(request, 'moneymanager/import.html', context)


@login_required
def import_csv_action(request):
    """Traite le fichier CSV uploadé"""
    if request.method == 'POST' and request.FILES.get('csv_file'):
        owner = request.user.owner_profile
        csv_file = request.FILES['csv_file']
        
        # Lecture du fichier
        try:
            decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        except UnicodeDecodeError:
            csv_file.seek(0)
            decoded_file = csv_file.read().decode('latin-1').splitlines()
            
        reader = csv.DictReader(decoded_file, delimiter=';')

        auto_rules = AutoCategoryRule.objects.filter(owner=owner)
        
        count_added = 0
        count_auto = 0

        for row in reader:
            date_str = row.get('dateOp')
            label = row.get('label', '')
            amount_raw = row.get('amount', '0')
            
            if not date_str or not amount_raw:
                continue

            amount_str = amount_raw.replace(',', '.').replace(' ', '')
            amount = Decimal(amount_str)

            unique_string = f"{date_str}_{label}_{amount}"
            bank_ref = hashlib.md5(unique_string.encode('utf-8')).hexdigest()

            # Création si n'existe pas
            if not Transaction.objects.filter(bank_reference=bank_ref).exists():

                # --- LE MOTEUR DE TRI AUTOMATIQUE ---
                matched_category = None
                is_processed = False
                
                # On teste chaque règle
                for rule in auto_rules:
                    # Si le mot-clé (en minuscules) est dans le libellé de la banque (en minuscules)
                    if rule.keyword.lower() in label.lower():
                        matched_category = rule.category
                        is_processed = True
                        break

                Transaction.objects.create(
                    owner=owner,
                    bank_reference=bank_ref,
                    bank_date=date_str,
                    bank_label=label[:255],
                    bank_category=row.get('category', '')[:100],
                    bank_amount=amount,
                    custom_date=date_str,
                    custom_amount=amount,
                    category=matched_category,
                    is_processed=is_processed
                )

                if is_processed and matched_category:
                    count_auto += 1
                    link = CategoryEnvelopeLink.objects.filter(owner=owner, category=matched_category).first()
                    if link:
                        if link.link_type == 'PROVISION':
                            link.envelope.amount -= amount
                        elif link.link_type == 'EXPENSE':
                            link.envelope.amount += amount
                        link.envelope.save()
                        
                count_added += 1
                
        now = datetime.now()

        messages.success(request, f"Import terminé : {count_added} nouveautés dont {count_auto} classées auto ! ✨")

        return redirect('moneymanager:dashboard', year=now.year, month=now.month)
    
    return redirect('moneymanager:import_page')
