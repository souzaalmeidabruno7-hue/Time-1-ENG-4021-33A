"""Pontuação de compatibilidade entre um artista e o evento descrito na busca.

Regras (documento "Regras de pontuação do match de compatibilidade"):
  - Preço       35 pontos: preço mínimo dentro do orçamento = 35;
                           até 20% acima do orçamento = 15; acima disso = 0.
  - Cidade      25 pontos: mesma cidade do evento = 25; outra cidade = 0.
  - Data        25 pontos: artista livre na data = 25; ocupado = 0.
  - Avaliação   15 pontos: nota média / 5 x 15; artista sem avaliação = 7,5.

Só entram na conta os critérios que o cliente informou. O resultado é a
porcentagem dos pontos obtidos sobre os pontos possíveis, arredondada
(,5 arredonda para cima).
"""

PESO_PRECO = 35
PESO_CIDADE = 25
PESO_DATA = 25
PESO_NOTA = 15
TOLERANCIA_PRECO = 1.2


def normalizar(texto):
    if texto is None:
        return ""
    return texto.strip().lower()


def pontos_preco(preco_minimo, orcamento):
    preco = float(preco_minimo)
    if preco <= orcamento:
        return PESO_PRECO
    if preco <= orcamento * TOLERANCIA_PRECO:
        return 15
    return 0


def pontos_cidade(cidade_artista, cidade_evento):
    artista = normalizar(cidade_artista)
    evento = normalizar(cidade_evento)
    if artista == evento or evento in artista:
        return PESO_CIDADE
    return 0


def pontos_nota(nota_media):
    if nota_media is None:
        return PESO_NOTA / 2
    return float(nota_media) / 5 * PESO_NOTA


def calcular_compatibilidade(artista, cidade, orcamento, data_informada, ocupado):
    """Devolve a compatibilidade de 0 a 100.

    artista: objeto Artista com nota_media (Artista.objects.com_nota()); cidade: texto ou ""; orcamento: float ou None;
    data_informada: True se o cliente escolheu uma data; ocupado: True se o
    artista não está livre nessa data.
    """
    obtidos = pontos_nota(artista.nota_media)
    possiveis = PESO_NOTA

    if orcamento is not None:
        obtidos = obtidos + pontos_preco(artista.preco_minimo, orcamento)
        possiveis = possiveis + PESO_PRECO

    if cidade != "":
        obtidos = obtidos + pontos_cidade(artista.cidade, cidade)
        possiveis = possiveis + PESO_CIDADE

    if data_informada:
        if not ocupado:
            obtidos = obtidos + PESO_DATA
        possiveis = possiveis + PESO_DATA

    # arredonda para o inteiro mais próximo; ,5 arredonda para cima
    return int(obtidos * 100 / possiveis + 0.5)
