from django.core.management.base import BaseCommand

from ArtConnect.dados_exemplo import popular
from ArtConnect.models import Categoria


class Command(BaseCommand):
    help = "Coloca os dados de exemplo no banco (só se ele estiver vazio)."

    def handle(self, *args, **options):
        if Categoria.objects.exists():
            self.stdout.write("O banco já tem dados. Nada foi alterado.")
            return
        popular()
