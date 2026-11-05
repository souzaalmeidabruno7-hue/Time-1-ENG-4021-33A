"""Lembretes automáticos de eventos próximos (Sprint 8).

Cliente e artista recebem um aviso 7 dias antes e outro 1 dia antes do evento.
Roda de dois jeitos:
  - sozinho, quando a pessoa abre o site (só para os contratos dela);
  - para todo mundo, com  python manage.py enviar_lembretes  (dá para agendar).
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from ArtConnect.models import Contrato, LembreteEnviado, Notificacao


def texto_do_lembrete(contrato, dias, para_cliente):
    if dias <= 0:
        quando = "Hoje é o dia"
    elif dias == 1:
        quando = "Amanhã é o dia"
    else:
        quando = "Faltam " + str(dias) + " dias"
    if para_cliente:
        texto = quando + " do seu evento com " + contrato.artista.nome_artistico
    else:
        texto = quando + " do seu show para " + contrato.cliente.perfil.nome
    texto = texto + " (" + contrato.data_evento.strftime("%d/%m/%Y") + ")."
    if contrato.status == "aguardando_pagamento" and para_cliente:
        texto = texto + " O pagamento ainda está pendente."
    return texto


def avisar(contrato, user, antecedencia, texto, link):
    """Cria o lembrete só se ele ainda não foi mandado."""
    if user is None:
        return False
    try:
        with transaction.atomic():
            LembreteEnviado.objects.create(contrato=contrato, user=user, antecedencia=antecedencia)
            Notificacao.objects.create(user=user, tipo="lembrete", texto=texto[:200], link=link)
        return True
    except IntegrityError:
        return False


def gerar_lembretes(user=None):
    """Gera os lembretes que estão faltando. Com user, só para os contratos dessa pessoa."""
    hoje = timezone.localdate()
    contratos = (Contrato.objects.filter(status__in=["aguardando_pagamento", "valor_retido"],
                                         data_evento__gte=hoje, data_evento__lte=hoje + timedelta(days=7))
                 .select_related("artista__user", "cliente__perfil"))
    if user is not None:
        contratos = contratos.filter(Q(cliente=user) | Q(artista__user=user))
    criados = 0
    for contrato in contratos:
        dias = (contrato.data_evento - hoje).days
        antecedencia = "7dias"
        if dias <= 1:
            antecedencia = "1dia"
        if avisar(contrato, contrato.cliente, antecedencia, texto_do_lembrete(contrato, dias, True),
                  reverse("painel") + "?aba=visao"):
            criados = criados + 1
        if avisar(contrato, contrato.artista.user, antecedencia, texto_do_lembrete(contrato, dias, False),
                  reverse("artista_painel") + "?aba=agenda"):
            criados = criados + 1
    return criados
