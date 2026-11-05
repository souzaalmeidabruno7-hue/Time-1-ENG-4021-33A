from django.core.management.base import BaseCommand

from ArtConnect.lembretes import gerar_lembretes


class Command(BaseCommand):
    help = "Avisa clientes e artistas sobre eventos nos próximos 7 dias (e na véspera)."

    def handle(self, *args, **options):
        criados = gerar_lembretes()
        self.stdout.write(str(criados) + " lembrete(s) enviado(s).")
