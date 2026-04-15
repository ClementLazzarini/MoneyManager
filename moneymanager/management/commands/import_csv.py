import csv
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from moneymanager.models import Transaction, Owner

class Command(BaseCommand):
    help = 'Importe les transactions bancaires depuis un fichier CSV situé dans le dossier DATA'

    def add_arguments(self, parser):
        # On demande juste le nom du fichier maintenant, plus tout le chemin
        parser.add_argument('filename', type=str, help='Le nom du fichier CSV (ex: export_trimestre1.csv)')

    def handle(self, *args, **kwargs):
        filename = kwargs['filename']
        owner_name = kwargs['owner'].capitalize()
        
        owner_obj, created = Owner.objects.get_or_create(name=owner_name)
        file_path = settings.BASE_DIR / 'DATA' / filename

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file, delimiter=';')
                
                count_added = 0
                count_skipped = 0

                for row in reader:
                    date_str = row['dateOp']
                    try:
                        if '/' in date_str:
                            bank_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        else:
                            bank_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Format de date ignoré pour la ligne : {date_str}"))
                        continue
                    
                    amount_str = row['amount'].replace(',', '.').replace(' ', '')
                    try:
                        bank_amount = float(amount_str)
                    except ValueError:
                        continue 

                    unique_string = f"{bank_date}_{row['label']}_{bank_amount}"
                    bank_ref = hashlib.md5(unique_string.encode('utf-8')).hexdigest()

                    if Transaction.objects.filter(bank_reference=bank_ref).exists():
                        count_skipped += 1
                        continue

                    Transaction.objects.create(
                        bank_reference=bank_ref,
                        owner=owner_obj,
                        bank_date=bank_date,
                        bank_label=row['label'][:255],
                        bank_category=row['category'][:100],
                        bank_amount=bank_amount,
                        custom_date=bank_date,
                        custom_amount=bank_amount,
                        comment=row['comment'] if row.get('comment') else ""
                    )
                    count_added += 1

            self.stdout.write(self.style.SUCCESS(f'✅ Import terminé ! {count_added} lignes ajoutées, {count_skipped} ignorées (déjà existantes).'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ Le fichier est introuvable au chemin : {file_path}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Une erreur est survenue : {str(e)}"))