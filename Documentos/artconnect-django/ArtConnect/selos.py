"""Selos de reputação dos artistas (Sprint 8).

Regras: Documentos/Sprint 8/regras-selos-reputacao.md
Cada selo é calculado na hora, a partir do que já está no banco.
"""
from datetime import timedelta

from django.utils import timezone

NOTA_BEM_AVALIADO = 4.5
HORAS_RESPONDE_RAPIDO = 24
DIAS_NOVO_TALENTO = 60

# (código, nome no selo, explicação mostrada ao passar o mouse)
SELOS = [
    ("bem_avaliado", "Bem avaliado", "Nota média 4,5 ou mais"),
    ("responde_rapido", "Responde rápido", "Responde aos pedidos em até 24 horas, em média"),
    ("confiavel", "Confiável", "Já concluiu eventos e não cancelou nenhum nos últimos 12 meses"),
    ("perfil_completo", "Perfil completo", "Tem descrição, estilo e portfólio"),
    ("novo_talento", "Novo talento", "Chegou há pouco tempo na plataforma"),
]


def media_horas_resposta(artista):
    """Tempo médio, em horas, entre o pedido chegar e o artista responder (ou None)."""
    total = 0
    quantidade = 0
    for proposta in artista.propostas.select_related("pedido"):
        horas = (proposta.criado_em - proposta.pedido.criado_em).total_seconds() / 3600
        total = total + horas
        quantidade = quantidade + 1
    if quantidade == 0:
        return None
    return total / quantidade


def codigos_dos_selos(artista):
    """Lista com os códigos dos selos que o artista tem. O artista precisa vir de Artista.objects.com_nota()."""
    codigos = []
    nota = artista.nota_media
    total_avaliacoes = artista.total_avaliacoes

    if nota is not None and float(nota) >= NOTA_BEM_AVALIADO:
        codigos.append("bem_avaliado")

    media = media_horas_resposta(artista)
    if media is not None and media <= HORAS_RESPONDE_RAPIDO:
        codigos.append("responde_rapido")

    um_ano_atras = timezone.now() - timedelta(days=365)
    concluidos = artista.contratos.filter(status="concluido").count()
    cancelou = artista.contratos.filter(cancelamento__cancelado_por="artista",
                                        cancelamento__criado_em__gte=um_ano_atras).exists()
    if concluidos >= 1 and not cancelou:
        codigos.append("confiavel")

    if artista.descricao and artista.estilo and artista.portfolio.exists():
        codigos.append("perfil_completo")

    novo = artista.criado_em >= timezone.now() - timedelta(days=DIAS_NOVO_TALENTO)
    if novo and total_avaliacoes == 0:
        codigos.append("novo_talento")
    return codigos


def selos_do_artista(artista):
    """Lista de (código, nome, explicação), na ordem de importância."""
    codigos = codigos_dos_selos(artista)
    lista = []
    for codigo, nome, explicacao in SELOS:
        if codigo in codigos:
            lista.append((codigo, nome, explicacao))
    return lista
