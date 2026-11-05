"""Dados de exemplo do ArtConnect (os mesmos da versão anterior do site).

Usado pelo comando  python manage.py popular_banco  e pelos testes.
"""
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from ArtConnect.models import (PRAZOS_SUPORTE, Artista, Avaliacao, Categoria, ChamadoSuporte, Contrato, Cupom,
                               Disponibilidade, Evento, Favorito, Mensagem, MensagemChamado, Notificacao, Pagamento,
                               PedidoOrcamento, Perfil, Portfolio, Proposta)

SENHA_PADRAO = "artconnect123"

CATEGORIAS = [
    ("Chefs & Buffet", "chefs-buffet", "Menus autorais, buffet e equipe de salão"),
    ("Mágicos", "magicos", "Mágica de perto, mentalismo e shows de palco"),
    ("DJs", "djs", "Sets sob medida com som e iluminação"),
    ("Cantores", "cantores", "Voz e violão, trio ou banda completa"),
    ("Foto & Vídeo", "foto-video", "Cobertura documental e filmes de evento"),
    ("Stand-up & Teatro", "standup-teatro", "Comédia, esquetes e performances ao vivo"),
    ("Arte Visual", "arte-visual", "Pintura ao vivo, murais e caricaturas"),
]

# (username, nome, email, telefone, cidade, papel)
USUARIOS = [
    ("admin", "Administrador ArtConnect", "admin@artconnect.com.br", "(21) 90000-0000", "Rio de Janeiro", "admin"),
    ("luiz", "Luiz Gullo", "luiz@exemplo.com", "(21) 98888-1111", "Rio de Janeiro", "cliente"),
    ("helena", "Helena Prado", "helena@exemplo.com", "(11) 97777-2222", "São Paulo", "cliente"),
    ("rafael", "Rafael Torres", "rafael@exemplo.com", "(21) 96666-3333", "Rio de Janeiro", "cliente"),
    ("selvaritmo", "Selva Ritmo", "contato@selvaritmo.com", "(11) 95555-4444", "São Paulo", "artista"),
    ("coletivomare", "Coletivo Maré", "contato@coletivomare.com", "(21) 94444-5555", "Rio de Janeiro", "artista"),
    ("neonsombra", "Neon Sombra", "contato@neonsombra.com", "(11) 93333-6666", "São Paulo", "artista"),
]

# (username ou None, nome_artistico, slug_categoria, estilo, cidade, preco, descricao)
ARTISTAS = [
    ("selvaritmo", "Selva Ritmo", "djs", "DJ Set", "São Paulo", 2400, "Sets de house e brasilidades para casamentos e festas."),
    (None, "Pulso Tropical", "djs", "Eletrônico", "Brasília", 2600, "Eletrônico tropical com iluminação própria."),
    (None, "Chef Raiz", "chefs-buffet", "Cozinha brasileira", "São Paulo", 3200, "Menu degustação com ingredientes locais."),
    (None, "Clara Veloso", "cantores", "MPB e Pop", "Salvador", 2100, "Voz e violão ou banda completa."),
    ("coletivomare", "Coletivo Maré", "cantores", "Jazz & MPB", "Rio de Janeiro", 1800, "Quinteto de jazz e MPB para eventos corporativos."),
    (None, "Ateliê Aurora", "arte-visual", "Pintura ao vivo", "Recife", 900, "Painéis pintados ao vivo durante o evento."),
    (None, "Mestre Ilusão", "magicos", "Mágica de perto", "Belo Horizonte", 1200, "Close-up e mentalismo para todas as idades."),
    (None, "Risada Tardia", "standup-teatro", "Stand-up", "São Paulo", 2860, "Stand-up de 45 minutos para eventos corporativos."),
    ("neonsombra", "Neon Sombra", "djs", "Eletrônico", "São Paulo", 3080, "Techno e eletrônico para aniversários e festas."),
    (None, "Vento Sul Trio", "cantores", "Acústico", "Sorocaba", 2530, "Set acústico de trio para festivais."),
    (None, "Estúdio Lume", "foto-video", "Eventos", "Rio de Janeiro", 2200, "Cobertura documental de foto e vídeo."),
]

# (cliente, artista, tipo, descricao, data, local, valor, status_contrato, status_pagamento, nota, comentario)
CONTRATOS = [
    ("luiz", "Selva Ritmo", "casamento", "Set de 3 horas", "2026-10-03", "Espaço Jardim Ipê, São Paulo", 4620, "valor_retido", "retido", None, None),
    ("luiz", "Coletivo Maré", "corporativo", "Banda completa", "2026-10-24", "Hotel Vila Nova, Rio de Janeiro", 7150, "aguardando_pagamento", "pendente", None, None),
    ("luiz", "Neon Sombra", "aniversario", "Set eletrônico", "2026-11-15", "Casa Amarela, São Paulo", 3080, "valor_retido", "retido", None, None),
    ("luiz", "Risada Tardia", "corporativo", "Stand-up de 45 min", "2026-07-19", "Auditório Central, São Paulo", 2860, "concluido", "liberado", 5, "Plateia não parou de rir. Recomendo!"),
    ("luiz", "Ateliê Aurora", "outro", "Painel ao vivo", "2026-05-30", "Praça das Artes, São Paulo", 1980, "concluido", "liberado", 5, "Painel lindo, todo mundo parou para ver."),
    ("helena", "Selva Ritmo", "casamento", "Set de 4 horas", "2026-09-20", "Espaço Jardim Ipê, São Paulo", 4800, "concluido", "liberado", 5, "Chegaram uma hora antes para passagem de som. A pista não esvaziou."),
    ("rafael", "Coletivo Maré", "corporativo", "Quinteto", "2026-09-10", "Hotel Vila Nova, Rio de Janeiro", 6500, "concluido", "liberado", 4, "Banda muito bem ensaiada, atrasou alguns minutos na montagem."),
    ("luiz", "Estúdio Lume", "formatura", "Cobertura de foto e vídeo", "2026-08-15", "Clube Monte Líbano, Rio de Janeiro", 2200, "concluido", "liberado", None, None),
]

MENSAGENS = [
    "Oi! Confirmo a data de 3 de outubro. Consigo chegar às 18h.",
    "Vocês têm som no local ou levo minha estrutura?",
    "Mando o roteiro das músicas até amanhã.",
]

# (cliente, slug_categoria, tipo, data, horario, duracao, convidados, local, observacoes)
PEDIDOS = [
    ("luiz", "djs", "casamento", "2026-12-12", "20:00", 4, 150, "Casa de Festas Lagoa, Rio de Janeiro", "Pista com house e MPB remix."),
    ("helena", "cantores", "aniversario", "2026-11-28", "19:00", 3, 60, "Salão Vila Madalena, São Paulo", "Voz e violão no jantar."),
    ("rafael", "djs", "corporativo", "2026-12-05", "21:00", 5, 200, "Rooftop Centro, Rio de Janeiro", ""),
]

# (artista, data, status, observacao)
AGENDA = [
    ("Selva Ritmo", "2026-11-21", "ocupado", "Show particular"),
    ("Selva Ritmo", "2026-12-05", "ocupado", "Festival em Campinas"),
    ("Neon Sombra", "2026-12-12", "ocupado", "Show já fechado"),
    ("Coletivo Maré", "2026-11-29", "ocupado", "Viagem"),
    ("Coletivo Maré", "2026-12-20", "disponivel", "Aceita evento de fim de ano"),
]

# (username, tipo, texto, link)
NOTIFICACOES = [
    ("luiz", "proposta", "Selva Ritmo enviou uma proposta de R$ 2.800 para o seu pedido de DJs.", "/painel?aba=pedidos"),
    ("luiz", "proposta", "Neon Sombra enviou uma contraproposta para 13/12/2026.", "/painel?aba=pedidos"),
    ("luiz", "pagamento", "O pagamento do contrato com Coletivo Maré está pendente.", "/painel?aba=historico"),
    ("selvaritmo", "mensagem", "Você tem uma conversa ativa com Luiz Gullo.", "/artista/painel?aba=propostas"),
]

# (codigo, descricao, tipo, valor, valor_minimo, desconto_maximo, validade)
CUPONS = [
    ("BEMVINDO10", "10% na primeira contratação", "percentual", 10, 500, 300, "2027-12-31"),
    ("ARTE50", "R$ 50 de desconto acima de R$ 1.000", "fixo", 50, 1000, None, "2027-12-31"),
    ("NATAL2025", "Campanha de Natal (encerrada)", "percentual", 15, 0, None, "2025-12-31"),
]

# (artista, tipo, titulo, url)
PORTFOLIO = [
    ("Selva Ritmo", "foto", "Set no casamento do Jardim Ipê", "/static/img/dj.jpg"),
    ("Coletivo Maré", "foto", "Quinteto no Hotel Vila Nova", "/static/img/jazz.jpg"),
    ("Neon Sombra", "foto", "Techno na Casa Amarela", "/static/img/eletronico.jpg"),
]


def avisar(mostrar, texto):
    if mostrar:
        print(texto)


def usuario(username):
    return User.objects.get(username=username)


def artista(nome):
    return Artista.objects.get(nome_artistico=nome)


@transaction.atomic
def popular(mostrar=True):
    avisar(mostrar, "Inserindo categorias...")
    for nome, slug, descricao in CATEGORIAS:
        Categoria.objects.create(nome=nome, slug=slug, descricao=descricao)

    avisar(mostrar, "Inserindo usuários...")
    for username, nome, email, telefone, cidade, papel in USUARIOS:
        novo = User.objects.create_user(username=username, email=email, password=SENHA_PADRAO)
        if papel == "admin":
            # o admin também entra no admin do Django (/django-admin/)
            novo.is_staff = True
            novo.is_superuser = True
            novo.save()
        Perfil.objects.create(user=novo, nome=nome, telefone=telefone, cidade=cidade, papel=papel)

    avisar(mostrar, "Inserindo artistas...")
    for username, nome, slug, estilo, cidade, preco, descricao in ARTISTAS:
        dono = None
        if username is not None:
            dono = usuario(username)
        Artista.objects.create(user=dono, nome_artistico=nome, categoria=Categoria.objects.get(slug=slug),
                               estilo=estilo, cidade=cidade, preco_minimo=preco, descricao=descricao)

    avisar(mostrar, "Inserindo eventos, contratos, pagamentos, avaliações e mensagens de exemplo...")
    for item in CONTRATOS:
        cliente = usuario(item[0])
        contratado = artista(item[1])
        evento = Evento.objects.create(cliente=cliente, tipo=item[2], categoria=contratado.categoria,
                                       data_evento=date.fromisoformat(item[4]), localizacao=item[5], orcamento=item[6])
        contrato = Contrato.objects.create(evento=evento, cliente=cliente, artista=contratado, descricao=item[3],
                                           data_evento=date.fromisoformat(item[4]), local=item[5],
                                           valor_total=item[6], status=item[7])
        Pagamento.objects.create(contrato=contrato, valor=item[6], metodo="pix", status=item[8])
        if item[9] is not None:
            avaliacao = Avaliacao.objects.create(contrato=contrato, artista=contratado, cliente=cliente,
                                                 nota=item[9], comentario=item[10])
            # as primeiras da lista ficam como as mais recentes (aparecem primeiro na home)
            Avaliacao.objects.filter(id=avaliacao.id).update(
                criado_em=timezone.now() - timedelta(minutes=CONTRATOS.index(item)))

    # Mensagens do artista Selva Ritmo para o cliente luiz, dentro do contrato de 03/10
    contrato_selva = Contrato.objects.get(artista__nome_artistico="Selva Ritmo", cliente__username="luiz")
    for posicao in range(len(MENSAGENS)):
        # horários diferentes para a conversa aparecer na ordem certa
        horas_atras = len(MENSAGENS) - posicao
        Mensagem.objects.create(contrato=contrato_selva, remetente=usuario("selvaritmo"), destinatario=usuario("luiz"),
                                conteudo=MENSAGENS[posicao], enviada_em=timezone.now() - timedelta(hours=horas_atras))

    avisar(mostrar, "Inserindo pedidos de orçamento, propostas e agenda dos artistas...")
    for cliente, slug, tipo, data, horario, duracao, convidados, local, observacoes in PEDIDOS:
        categoria = Categoria.objects.get(slug=slug)
        evento = Evento.objects.create(cliente=usuario(cliente), tipo=tipo, categoria=categoria,
                                       data_evento=date.fromisoformat(data), localizacao=local)
        PedidoOrcamento.objects.create(evento=evento, categoria=categoria, data_evento=date.fromisoformat(data),
                                       horario_inicio=time.fromisoformat(horario), duracao_horas=duracao,
                                       estimativa_convidados=convidados, local=local, observacoes=observacoes)

    # Duas respostas ao pedido do luiz: uma proposta normal e uma contraproposta de data
    pedido_luiz = PedidoOrcamento.objects.get(evento__cliente__username="luiz")
    Proposta.objects.create(pedido=pedido_luiz, artista=artista("Selva Ritmo"), valor=2800,
                            mensagem="Levo som e iluminação. Set de 4 horas com house e brasilidades.")
    Proposta.objects.create(pedido=pedido_luiz, artista=artista("Neon Sombra"), valor=3100,
                            mensagem="No dia 12 já tenho show. Consigo no dia seguinte, mesmo horário.",
                            data_sugerida=date(2026, 12, 13))
    pedido_luiz.status = "com_propostas"
    pedido_luiz.save()

    for nome, data, status, observacao in AGENDA:
        Disponibilidade.objects.create(artista=artista(nome), data=date.fromisoformat(data), status=status,
                                       observacao=observacao)

    avisar(mostrar, "Inserindo favoritos, notificações e portfólio...")
    for nome in ["Clara Veloso", "Chef Raiz"]:
        Favorito.objects.create(cliente=usuario("luiz"), artista=artista(nome))
    for posicao in range(len(NOTIFICACOES)):
        username, tipo, texto, link = NOTIFICACOES[posicao]
        aviso = Notificacao.objects.create(user=usuario(username), tipo=tipo, texto=texto, link=link)
        # a primeira da lista fica como a mais recente
        Notificacao.objects.filter(id=aviso.id).update(criada_em=timezone.now() - timedelta(minutes=posicao))
    for nome, tipo, titulo, url in PORTFOLIO:
        Portfolio.objects.create(artista=artista(nome), tipo=tipo, titulo=titulo, url=url)

    avisar(mostrar, "Inserindo cupons, chamado de suporte e resposta de avaliação (Sprint 8)...")
    for codigo, descricao, tipo, valor, minimo, maximo, validade in CUPONS:
        Cupom.objects.create(codigo=codigo, descricao=descricao, tipo=tipo, valor=valor, valor_minimo=minimo,
                             desconto_maximo=maximo, validade=date.fromisoformat(validade))

    chamado = ChamadoSuporte.objects.create(
        user=usuario("luiz"), categoria="pagamento",
        contrato=Contrato.objects.get(artista__nome_artistico="Coletivo Maré", cliente__username="luiz"),
        assunto="Não consegui pagar o contrato do Coletivo Maré",
        descricao="A data do evento passou e o botão de pagar sumiu. O que eu faço?",
        prazo_resposta=timezone.now() + timedelta(hours=PRAZOS_SUPORTE["pagamento"]), status="em_andamento",
    )
    MensagemChamado.objects.create(chamado=chamado, autor=usuario("admin"), da_equipe=True,
                                   texto="Oi, Luiz! Como a data passou, o contrato precisa ser cancelado ou remarcado "
                                         "com o artista. Já avisamos o Coletivo Maré.")

    avaliacao = Avaliacao.objects.get(artista__nome_artistico="Selva Ritmo", cliente__username="helena")
    avaliacao.resposta = "Obrigado, Helena! Foi um prazer tocar no casamento de vocês."
    avaliacao.respondida_em = timezone.now()
    avaliacao.save()

    avisar(mostrar, "Banco populado! Usuário de teste: luiz / senha: " + SENHA_PADRAO)
