"""Filtros e componentes visuais usados nos templates.

Nos templates:  {% load artconnect %}
Exemplos:       {{ contrato.valor_total|moeda }}   {% selo "Pago" "ok" %}
"""
import os
from datetime import datetime

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from ArtConnect.models import STATUS_CONTRATO, STATUS_PAGAMENTO, STATUS_PROPOSTA, TIPOS_EVENTO
from ArtConnect.politicas import link_embed

register = template.Library()

PASTA_FOTOS = os.path.join(settings.BASE_DIR, "ArtConnect", "static", "img")

# palavra no estilo/categoria do artista -> arquivo em static/img
FOTOS_POR_ESTILO = [
    ("eletr", "eletronico"),
    ("dj", "dj"),
    ("jazz", "jazz"),
    ("acústico", "folk"),
    ("folk", "folk"),
    ("cantor", "jazz"),
    ("mpb", "jazz"),
    ("chef", "chef"),
    ("buffet", "chef"),
    ("cozinha", "chef"),
    ("mágic", "magico"),
    ("foto", "foto"),
    ("stand", "standup"),
    ("teatro", "standup"),
    ("visual", "visual"),
    ("pintura", "visual"),
]

CORES_SELO = {
    "stage": "bg-stage/15 text-stage",
    "ink": "bg-ink/10 text-ink",
    "aviso": "bg-amber-500/15 text-amber-800",
    "ok": "bg-ok/15 text-ok",
    "neutro": "bg-ink/5 text-ink-soft",
}


def traduzir(lista, codigo):
    for item in lista:
        if item[0] == codigo:
            return item[1]
    return codigo


# ---------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------
@register.filter
def moeda(valor):
    if valor is None or valor == "":
        return "R$ 0"
    texto = "{:,.0f}".format(float(valor)).replace(",", ".")
    return "R$ " + texto


@register.filter
def data_br(valor):
    if valor is None or valor == "":
        return "A definir"
    if isinstance(valor, datetime) and timezone.is_aware(valor):
        valor = timezone.localtime(valor)
    return valor.strftime("%d/%m/%Y")


@register.filter
def tipo_evento(valor):
    return traduzir(TIPOS_EVENTO, valor)


@register.filter
def status_pagamento(valor):
    return traduzir(STATUS_PAGAMENTO, valor)


@register.filter
def status_proposta(valor):
    return traduzir(STATUS_PROPOSTA, valor)


@register.filter
def status_contrato(valor):
    return traduzir(STATUS_CONTRATO, valor)


@register.filter
def tom_pagamento(status):
    if status == "retido":
        return "stage"
    if status == "liberado":
        return "ink"
    if status == "pendente":
        return "aviso"
    return "neutro"


@register.filter
def embed_video(url):
    return link_embed(url)


@register.filter
def foto_artista(artista):
    """Devolve a URL da foto do artista, ou "" se não houver foto."""
    if getattr(artista, "foto_url", ""):
        return artista.foto_url
    texto = ""
    for campo in [getattr(artista, "estilo", ""), getattr(artista, "categoria", ""), getattr(artista, "descricao", "")]:
        if campo:
            texto = texto + " " + str(campo).lower()
    for palavra, arquivo in FOTOS_POR_ESTILO:
        if palavra in texto and os.path.exists(os.path.join(PASTA_FOTOS, arquivo + ".jpg")):
            return static("img/" + arquivo + ".jpg")
    return ""


@register.filter
def item(dicionario, chave):
    """Permite usar dicionario[chave] no template: {{ icones|item:n.tipo }}"""
    return dicionario.get(chave, "")


# ---------------------------------------------------------------
# Componentes (antes eram macros no _ui.html)
# ---------------------------------------------------------------
@register.simple_tag
def estrelas(nota, classe=""):
    cheias = int(float(nota or 0) + 0.5)
    lista = []
    for i in range(5):
        cor = "text-stage" if i < cheias else "text-line"
        lista.append((cor,))
    return format_html('<span class="{}" aria-label="{} de 5 estrelas">{}</span>',
                       classe, nota, format_html_join("", '<span class="{}">★</span>', lista))


@register.simple_tag
def foto(artista, classe):
    url = foto_artista(artista)
    if url:
        return format_html('<img src="{}" alt="{}" loading="lazy" class="{} object-cover">',
                           url, artista.nome_artistico, classe)
    return format_html('<div class="{} flex items-center justify-center bg-ink font-display text-2xl uppercase '
                       'text-cream/80" aria-hidden="true">{}</div>', classe, artista.nome_artistico[:1])


@register.simple_tag
def selo(texto, tom="neutro"):
    return format_html('<span class="inline-flex shrink-0 items-center rounded-full px-3 py-1 font-mono text-[10px] '
                       'uppercase tracking-[0.12em] {}">{}</span>', CORES_SELO.get(tom, CORES_SELO["neutro"]), texto)


@register.simple_tag
def vazio(texto):
    return format_html('<p class="rounded-2xl border border-dashed border-line bg-cream px-6 py-10 text-center '
                       'text-sm text-ink-soft">{}</p>', texto)


@register.simple_tag
def kpi(titulo, valor, detalhe=""):
    linha_detalhe = ""
    if detalhe:
        linha_detalhe = format_html('<p class="mt-1 text-xs text-ink-soft">{}</p>', detalhe)
    return format_html('<div class="rounded-2xl border border-line bg-cream p-5 ring-1 ring-black/5">'
                       '<p class="font-mono text-[11px] uppercase tracking-[0.15em] text-ink-soft">{}</p>'
                       '<p class="mt-2 font-display text-3xl tracking-tight">{}</p>{}</div>',
                       titulo, valor, linha_detalhe)


@register.simple_tag
def aba(rotulo, url, chave, atual, contador=0, parametro="aba"):
    """Botão de aba: {% aba "Histórico" url_painel "historico" aba %} vira um link para url?aba=historico."""
    if chave == atual:
        estilo = "bg-ink text-cream"
    else:
        estilo = "border border-line text-ink-soft hover:bg-cream hover:text-ink"
    marcador = ""
    if contador:
        marcador = format_html('<span class="ml-2 rounded-full bg-stage px-2 py-0.5 text-[10px] text-cream">{}</span>',
                               contador)
    return format_html('<a href="{}?{}={}" class="rounded-full px-4 py-2 text-sm font-semibold transition-colors {}">{}{}</a>',
                       url, parametro, chave, estilo, rotulo, marcador)


# ---------------------------------------------------------------
# Cores dos selos de status (escolhem o "tom" do componente selo)
# ---------------------------------------------------------------
@register.filter
def tom_contrato(status):
    if status == "valor_retido":
        return "stage"
    if status == "concluido":
        return "ink"
    if status in ("aguardando_pagamento", "pendente"):
        return "aviso"
    return "neutro"


@register.filter
def tom_proposta(status):
    if status == "aceita":
        return "ok"
    if status == "enviada":
        return "aviso"
    return "neutro"


@register.filter
def tom_papel(papel):
    if papel == "artista":
        return "stage"
    if papel == "admin":
        return "ink"
    return "neutro"


@register.filter
def tom_portfolio(tipo):
    if tipo == "video":
        return "stage"
    if tipo == "audio":
        return "ink"
    return "neutro"


@register.filter
def sem_underline(texto):
    return str(texto).replace("_", " ")


@register.filter
def repetir_estrela(nota):
    return "★" * int(nota or 0)


@register.filter
def icone_notificacao(tipo):
    icones = {"proposta": "✉", "contrato": "✓", "pagamento": "R$", "cancelamento": "✕",
              "mensagem": "💬", "avaliacao": "★", "moderacao": "⚑"}
    return icones.get(tipo, "•")


@register.filter
def texto(valor):
    """Converte para texto, para juntar com |add:" ..." no template."""
    return str(valor)
