from django.db import models

class Category(models.Model):
    """
    Vos propres catégories ou enveloppes.
    """
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

class Owner(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    # ==========================================
    # 1. DONNÉES BRUTES (Issues de l'import)
    # ==========================================
    bank_reference = models.CharField(
        max_length=255, 
        db_index=True, 
        help_text="Identifiant logique/unique fourni par la banque pour éviter les doublons"
    )
    bank_date = models.DateField(
        help_text="Date réelle de l'opération bancaire"
    )
    bank_label = models.CharField(
        max_length=255, 
        help_text="Le libellé brut (ex: 'CB CARREFOUR TOULOUSE')"
    )
    bank_category = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="La catégorie automatique donnée par la banque"
    )
    bank_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Le montant réel prélevé ou viré par la banque"
    )

    # ==========================================
    # 2. DONNÉES UTILISATEUR (Modifiables via l'interface)
    # ==========================================
    custom_date = models.DateField(
        help_text="Date sur laquelle tu souhaites imputer cette ligne (par défaut égale à bank_date)"
    )
    custom_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Le montant que tu comptes réellement. Modifiable pour diviser une dépense."
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        help_text="Votre catégorie personnalisée"
    )
    comment = models.TextField(
        blank=True, 
        null=True, 
        help_text="Un petit mot pour se souvenir du pourquoi du comment"
    )

    owner = models.ForeignKey(
        Owner, 
        on_delete=models.CASCADE, 
        null=True,
        related_name='transactions'
    )

    # ==========================================
    # 3. STATUT (Pour le flux de travail)
    # ==========================================
    is_processed = models.BooleanField(
        default=False, 
        help_text="Permet de savoir si tu as déjà validé/catégorisé cette ligne"
    )

    class Meta:
        ordering = ['-bank_date']

    def __str__(self):
        return f"{self.custom_date} | {self.bank_label} | {self.custom_amount}€"


class DefaultBudget(models.Model):
    """
    Le budget "classique" de base pour une catégorie donnée.
    """
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='default_budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Budget de base par défaut")

    class Meta:
        unique_together = ('owner', 'category')
        ordering = ['category__name']

    def __str__(self):
        return f"Défaut {self.owner.name} - {self.category.name} : {self.amount}€"


class MonthlyBudget(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="L'enveloppe prévue pour ce mois")

    class Meta:
        unique_together = ('owner', 'category', 'year', 'month')
        ordering = ['-year', '-month', 'category__name']

    def __str__(self):
        return f"{self.owner.name} - {self.category.name} ({self.month}/{self.year}) : {self.target_amount}€"
    

class AccountBalance(models.Model):
    """Stocke le solde global actuel de tous les comptes cumulés"""
    owner = models.OneToOneField(Owner, on_delete=models.CASCADE, related_name='global_balance')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="L'argent total actuel en banque")
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Solde {self.owner.name} : {self.balance} €"


class GlobalEnvelope(models.Model):
    """Les pots ou sous-comptes virtuels (Sécurité, Voyage, Avances...)"""
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, related_name='global_envelopes')
    name = models.CharField(max_length=100, help_text="Ex: Big voyage, Sécurité, Holidays 2025")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Montant alloué (peut être négatif pour une avance)")
    comment = models.CharField(max_length=255, blank=True, null=True, help_text="Notes (Ex: RTX)")
    
    class Meta:
        ordering = ['-amount'] # Affiche les plus grosses enveloppes en premier

    def __str__(self):
        return f"{self.name} ({self.owner.name}) : {self.amount} €"
