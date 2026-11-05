"""Regras de negócio escritas pelo grupo, transformadas em código.

- Cancelamento e reembolso: Documentos/Sprint 6/politica-cancelamento-reembolso.md
- Links de portfólio: Documentos/Sprint 7/regras-moderacao-denuncias.md
"""
from urllib.parse import parse_qs, urlparse


def percentual_reembolso(cancelado_por, dias_antecedencia, horas_desde_contrato):
    """Quanto do valor pago volta para o cliente (0 a 100)."""
    if cancelado_por == "artista":
        return 100
    # arrependimento: até 24h depois de aceitar, se o evento estiver a mais de 7 dias
    if horas_desde_contrato <= 24 and dias_antecedencia > 7:
        return 100
    if dias_antecedencia >= 30:
        return 100
    if dias_antecedencia >= 15:
        return 70
    if dias_antecedencia >= 7:
        return 50
    return 0


def dividir_valor(valor_pago, percentual):
    """Devolve (valor que volta ao cliente, valor que fica com o artista)."""
    reembolso = round(float(valor_pago) * percentual / 100, 2)
    artista = round(float(valor_pago) - reembolso, 2)
    return reembolso, artista


def id_video(url):
    """Devolve ("youtube" ou "vimeo", id) para links de vídeo conhecidos, ou None."""
    try:
        partes = urlparse(url)
    except ValueError:
        return None
    host = partes.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    caminho = partes.path.strip("/").split("/")

    if host == "youtu.be" and caminho[0] != "":
        return ("youtube", caminho[0])
    if host == "youtube.com":
        if caminho[0] == "watch":
            valores = parse_qs(partes.query).get("v", [""])
            if valores[0] != "":
                return ("youtube", valores[0])
        if caminho[0] in ("shorts", "embed") and len(caminho) > 1:
            return ("youtube", caminho[1])
    if host == "vimeo.com" and caminho[0].isdigit():
        return ("vimeo", caminho[0])
    return None


def link_embed(url):
    """URL para colocar no <iframe> do vídeo, ou "" se não for YouTube/Vimeo."""
    video = id_video(url)
    if video is None:
        return ""
    servico, codigo = video
    if not codigo.replace("-", "").replace("_", "").isalnum():
        return ""
    if servico == "youtube":
        return "https://www.youtube-nocookie.com/embed/" + codigo
    return "https://player.vimeo.com/video/" + codigo
