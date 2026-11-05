from django.core.management.base import BaseCommand

from ArtConnect.dados_exemplo import popular, popular_cupons
from ArtConnect.models import Categoria, Cupom


class Command(BaseCommand):
    help = "Coloca os dados de exemplo no banco (só se ele estiver vazio)."

    def handle(self, *args, **options):
        if not Categoria.objects.exists():
            popular()
            return
        if not Cupom.objects.exists():
            # banco criado antes da Sprint 8: só faltam os cupons de exemplo
            popular_cupons()
            self.stdout.write("Cupons de exemplo da Sprint 8 adicionados.")
            return
        self.stdout.write("O banco já tem dados. Nada foi alterado.")
