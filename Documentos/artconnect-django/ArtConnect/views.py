import csv
import hashlib
import secrets
import uuid
from datetime import date, datetime, time, timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

from ArtConnect.lembretes import gerar_lembretes
from ArtConnect.match import calcular_compatibilidade
from ArtConnect.models import (CATEGORIAS_SUPORTE, ESTADOS, IDADE_MAXIMA, IDADE_MINIMA, MESES, MOTIVOS_DENUNCIA, SIGLAS_ESTADOS, PRAZOS_SUPORTE, TIPOS_EVENTO, Artista, Avaliacao,
                               Cancelamento, Categoria, ChamadoSuporte, Contrato, Cupom, Denuncia, Disponibilidade,
                               Evento, Favorito, Mensagem, MensagemChamado, Notificacao, Pagamento, PedidoOrcamento,
                               Perfil, Portfolio, Proposta, TokenSenha, calcular_idade)
from ArtConnect.politicas import calcular_desconto, dividir_valor, link_embed, percentual_reembolso
from ArtConnect.selos import selos_do_artista
from ArtConnect.templatetags.artconnect import data_br, moeda

MINUTOS_VALIDADE_TOKEN = 30
LIMITE_PORTFOLIO = 12

METODOS_PAGAMENTO = [
    ("pix", "Pix"),
    ("boleto", "Boleto bancário"),
]

FAIXAS_REEMBOLSO = [
    ("30 dias ou mais", "100%"),
    ("15 a 29 dias", "70%"),
    ("7 a 14 dias", "50%"),
    ("Menos de 7 dias", "0%"),
]

# Classes do Tailwind reaproveitadas em vários templates ({{ ui.rotulo }}, {{ ui.campo_claro }}...)
UI = {
    "rotulo": "font-mono text-[11px] uppercase tracking-[0.15em] text-ink-soft",
    "rotulo_escuro": "font-mono text-[11px] uppercase tracking-[0.15em] text-cream/60",
    "campo_claro": "mt-2 w-full rounded-xl border border-line bg-paper px-4 py-3 text-sm text-ink outline-none "
                   "placeholder:text-ink-soft/50 focus:border-stage",
    "campo_escuro": "mt-2 w-full rounded-lg border border-cream/20 bg-ink px-3 py-2.5 text-sm text-cream "
                    "placeholder:text-cream/30 ring-1 ring-white/5 focus:border-stage focus:outline-none",
    "botao_stage": "rounded-full bg-stage px-7 py-3 font-semibold text-cream ring-1 ring-black/5 transition-colors hover:bg-ink",
    "botao_contorno": "rounded-full border border-line px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-cream",
}


# ---------------------------------------------------------------
# Funções de apoio
# ---------------------------------------------------------------
def hoje():
    return timezone.localdate()


def id_valido(texto):
    try:
        uuid.UUID(str(texto))
        return True
    except ValueError:
        return False


def numero_ou_none(texto):
    texto = texto.strip().replace(",", ".")
    if texto == "":
        return None
    return float(texto)


def data_ou_none(texto):
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def papel_de(user):
    """Papel do usuário logado: cliente, artista ou admin (None para visitantes)."""
    if not user.is_authenticated:
        return None
    try:
        return user.perfil.papel
    except Perfil.DoesNotExist:
        if user.is_superuser:
            return "admin"
        return "cliente"


def nome_de(user):
    try:
        return user.perfil.nome
    except Perfil.DoesNotExist:
        return user.username


def artista_logado(request):
    if not request.user.is_authenticated:
        return None
    return Artista.objects.com_nota().filter(user=request.user).first()


def destino_painel(request):
    papel = papel_de(request.user)
    if papel == "artista":
        return reverse("artista_painel")
    if papel == "admin":
        return reverse("admin_dashboard")
    return reverse("painel")


def url_com_aba(nome, aba):
    return reverse(nome) + "?aba=" + aba


def link_interno(texto):
    """Só aceita caminhos do próprio site (evita redirecionar para outro domínio)."""
    return texto.startswith("/") and not texto.startswith("//")


def notificar(user, tipo, texto, link):
    """Cria um aviso no sino do usuário. Artista sem conta (user vazio) é ignorado."""
    if user is None:
        return
    Notificacao.objects.create(user=user, tipo=tipo, texto=texto[:200], link=link)


def variaveis_globais(request):
    """Context processor: variáveis disponíveis em todos os templates."""
    notificacoes_novas = 0
    usuario_nome = None
    if request.user.is_authenticated:
        # Sprint 8: avisos de eventos nos próximos 7 dias (só cria os que ainda não existem)
        gerar_lembretes(request.user)
        notificacoes_novas = Notificacao.objects.filter(user=request.user, lida=False).count()
        usuario_nome = nome_de(request.user)
    return {
        "usuario_nome": usuario_nome,
        "usuario_papel": papel_de(request.user),
        "notificacoes_novas": notificacoes_novas,
        "ui": UI,
    }


# ---------------------------------------------------------------
# Controle de acesso (além do login_required do Django)
# ---------------------------------------------------------------
def admin_obrigatorio(funcao):
    @wraps(funcao)
    def verificar(request, *args, **kwargs):
        if papel_de(request.user) != "admin":
            messages.error(request, "Acesso restrito ao administrador.")
            return redirect("index")
        return funcao(request, *args, **kwargs)
    return verificar


def artista_obrigatorio(funcao):
    @wraps(funcao)
    def verificar(request, *args, **kwargs):
        if papel_de(request.user) != "artista" or artista_logado(request) is None:
            messages.error(request, "Área exclusiva para artistas.")
            return redirect("index")
        return funcao(request, *args, **kwargs)
    return verificar


# ---------------------------------------------------------------
# Página inicial: busca com ordenação por compatibilidade
# ---------------------------------------------------------------
def index(request):
    categoria = request.GET.get("categoria", "")
    cidade = request.GET.get("cidade", "").strip()
    orcamento_texto = request.GET.get("orcamento", "").strip()
    data_texto = request.GET.get("data", "").strip()

    orcamento = None
    if orcamento_texto != "":
        try:
            orcamento = numero_ou_none(orcamento_texto)
            if orcamento <= 0:
                orcamento = None
                messages.error(request, "O orçamento precisa ser maior que zero.")
        except ValueError:
            messages.error(request, "Informe o orçamento só com números.")

    data_evento = None
    if data_texto != "":
        data_evento = data_ou_none(data_texto)
        if data_evento is None:
            messages.error(request, "Data inválida.")

    busca = Artista.objects.com_nota().filter(ativo=True)
    if categoria.isdigit():
        busca = busca.filter(categoria_id=categoria)
    busca = busca.order_by(F("nota_media").desc(nulls_last=True), "-total_avaliacoes", "nome_artistico")
    artistas = list(busca)

    ocupados = []
    if data_evento is not None:
        for artista_id in Disponibilidade.objects.filter(data=data_evento, status="ocupado").values_list("artista_id", flat=True):
            ocupados.append(artista_id)
        for artista_id in Contrato.objects.filter(data_evento=data_evento).exclude(status="cancelado").values_list("artista_id", flat=True):
            ocupados.append(artista_id)

    usar_match = cidade != "" or orcamento is not None or data_evento is not None
    for artista in artistas:
        artista.ocupado = artista.id in ocupados
        artista.compatibilidade = calcular_compatibilidade(
            artista, cidade, orcamento, data_evento is not None, artista.ocupado
        )
    if usar_match:
        # ordena pela compatibilidade; em caso de empate, pela nota
        artistas.sort(key=lambda a: (a.compatibilidade, float(a.nota_media or 0)), reverse=True)

    cidades = []
    posicao = 0
    for artista in artistas:
        if artista.cidade not in cidades:
            cidades.append(artista.cidade)
        # atraso da animação de cada linha dos resultados
        artista.selos = selos_do_artista(artista)
        artista.atraso = posicao * 80
        artista.atraso_barra = posicao * 90 + 100
        posicao = posicao + 1
    cidades.sort()

    # mantém cidade, orçamento e data quando o cliente clica numa categoria
    filtros_extras = ""
    if cidade != "":
        filtros_extras = filtros_extras + "&cidade=" + cidade
    if orcamento_texto != "":
        filtros_extras = filtros_extras + "&orcamento=" + orcamento_texto
    if data_texto != "":
        filtros_extras = filtros_extras + "&data=" + data_texto

    depoimentos = (Avaliacao.objects.filter(oculta=False, comentario__isnull=False).exclude(comentario="")
                   .select_related("cliente__perfil", "artista", "contrato__evento").order_by("-criado_em")[:3])
    ativos = Artista.objects.filter(ativo=True)
    foto_hero = ""
    if (settings.BASE_DIR / "ArtConnect" / "static" / "img" / "hero.jpg").exists():
        foto_hero = static("img/hero.jpg")

    passos = [
        ("01", "Peça um orçamento", "Conte data, horário, duração, local e número de convidados.",
         reverse("orcamento"), "Pedir orçamento"),
        ("02", "Compare por compatibilidade", "Veja quem combina com categoria, orçamento, região e agenda.",
         reverse("index") + "#artistas", "Ver artistas"),
        ("03", "Contrate com segurança", "O pagamento fica retido e só é liberado após o evento.",
         reverse("painel"), "Meu painel"),
    ]
    contexto = {
        "artistas": artistas,
        "cidades": cidades,
        "categorias": Categoria.objects.all(),
        "depoimentos": depoimentos,
        "categoria_atual": categoria,
        "cidade_atual": cidade,
        "orcamento_atual": orcamento_texto,
        "data_atual": data_texto,
        "filtros_extras": filtros_extras,
        "usar_match": usar_match,
        "total_artistas": ativos.count(),
        "total_cidades": ativos.values("cidade").distinct().count(),
        "foto_hero": foto_hero,
        "passos": passos,
        "passos_pagamento": ["Você contrata", "O valor fica retido com segurança", "O artista recebe após o evento"],
    }
    return render(request, "index.html", contexto)


def artista_detalhe(request, artista_id):
    artista = None
    if id_valido(artista_id):
        artista = Artista.objects.com_nota().filter(id=artista_id).first()
    # perfil suspenso pela moderação só continua visível para o administrador
    if artista is not None and not artista.ativo and papel_de(request.user) != "admin":
        artista = None
    if artista is None:
        messages.error(request, "Artista não encontrado.")
        return redirect("index")

    avaliacoes = artista.avaliacoes.filter(oculta=False).select_related("cliente__perfil").order_by("-criado_em")
    portfolio = list(artista.portfolio.all())
    for item in portfolio:
        item.embed = ""
        if item.tipo == "video":
            item.embed = link_embed(item.url)
    favorito = False
    if papel_de(request.user) == "cliente":
        favorito = Favorito.objects.filter(cliente=request.user, artista=artista).exists()

    condicoes = [
        ("Cachê inicial", moeda(artista.preco_minimo)),
        ("Categoria", artista.categoria),
        ("Cidade de atuação", artista.cidade),
        ("Pagamento", "retido até o evento"),
    ]
    contexto = {
        "artista": artista,
        "selos": selos_do_artista(artista),
        "avaliacoes": avaliacoes,
        "portfolio": portfolio,
        "favorito": favorito,
        "motivos": MOTIVOS_DENUNCIA,
        "condicoes": condicoes,
    }
    return render(request, "artista.html", contexto)


# ---------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------
def entrar(request):
    proximo = request.GET.get("next", "")
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lower()
        senha = request.POST.get("password", "")

        usuario = authenticate(request, username=username, password=senha)
        if usuario is None:
            messages.error(request, "Usuário ou senha incorretos.")
            return render(request, "login.html", {"username": username}, status=401)

        perfil = Perfil.objects.filter(user=usuario).first()
        if perfil is not None and perfil.menor_de_idade:
            # menor de 18 anos não entra, mesmo com a senha certa
            messages.error(request, "É preciso ter ao menos " + str(IDADE_MINIMA) + " anos para entrar na ArtConnect.")
            return render(request, "login.html", {"username": username}, status=403)

        login(request, usuario)
        if request.POST.get("remember") != "on":
            request.session.set_expiry(0)   # a sessão acaba quando o navegador fecha
        if link_interno(proximo):
            return redirect(proximo)
        return redirect(destino_painel(request))

    if proximo != "" and not request.user.is_authenticated:
        messages.error(request, "Entre na sua conta para continuar.")
    return render(request, "login.html", {"username": ""})


def sair(request):
    logout(request)
    messages.success(request, "Você saiu da sua conta.")
    return redirect("index")


# ---------------------------------------------------------------
# Recuperação de senha com token
# ---------------------------------------------------------------
def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def buscar_token_valido(token):
    return TokenSenha.objects.filter(token_hash=hash_token(token), usado=False, expira_em__gt=timezone.now()).first()


def esqueci_senha(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if "@" not in email:
            messages.error(request, "Informe um e-mail válido.")
            return render(request, "esqueci_senha.html", {"email": email}, status=400)

        usuario = User.objects.filter(email=email).first()
        if usuario is not None:
            token = secrets.token_urlsafe(32)
            with transaction.atomic():
                # um pedido novo invalida os links anteriores
                TokenSenha.objects.filter(user=usuario, usado=False).update(usado=True)
                TokenSenha.objects.create(user=usuario, token_hash=hash_token(token),
                                          expira_em=timezone.now() + timedelta(minutes=MINUTOS_VALIDADE_TOKEN))
            link = request.build_absolute_uri(reverse("redefinir_senha", args=[token]))
            corpo = (
                "Olá, " + nome_de(usuario) + "!\n\n"
                "Recebemos um pedido para redefinir a sua senha do ArtConnect.\n"
                "Use o link abaixo em até " + str(MINUTOS_VALIDADE_TOKEN) + " minutos:\n\n"
                + link + "\n\n"
                "Se não foi você, ignore este e-mail. Sua senha continua a mesma."
            )
            send_mail("Redefinição de senha · ArtConnect", corpo, None, [usuario.email])

        # mesma resposta com ou sem conta, para não revelar quais e-mails estão cadastrados
        messages.success(request, "Se esse e-mail estiver cadastrado, você vai receber um link para criar uma nova senha.")
        return redirect("login")

    return render(request, "esqueci_senha.html", {"email": ""})


def redefinir_senha(request, token):
    registro = buscar_token_valido(token)
    if registro is None:
        messages.error(request, "Link inválido ou expirado. Peça um novo.")
        return redirect("esqueci_senha")

    if request.method == "POST":
        senha = request.POST.get("senha", "")
        confirmar = request.POST.get("confirmar", "")
        if len(senha) < 8:
            messages.error(request, "A senha precisa ter ao menos 8 caracteres.")
        elif senha != confirmar:
            messages.error(request, "As senhas não coincidem.")
        else:
            with transaction.atomic():
                registro.user.set_password(senha)
                registro.user.save()
                registro.usado = True
                registro.save()
            messages.success(request, "Senha alterada! Entre com a nova senha.")
            return redirect("login")
        return render(request, "redefinir_senha.html", {"token": token}, status=400)

    return render(request, "redefinir_senha.html", {"token": token})


# ---------------------------------------------------------------
# Cadastro de usuário
# ---------------------------------------------------------------
def anos_de_nascimento():
    """Anos que aparecem na lista: do mais recente que pode ter 18 anos até 120 anos atrás."""
    ano_atual = hoje().year
    anos = []
    for ano in range(ano_atual - IDADE_MINIMA, ano_atual - IDADE_MAXIMA - 1, -1):
        anos.append(ano)
    return anos


def contexto_nascimento():
    dias = []
    for dia in range(1, 32):
        dias.append(dia)
    return {"estados": ESTADOS, "dias": dias, "meses": MESES, "anos": anos_de_nascimento(), "idade_minima": IDADE_MINIMA}


def validar_estado_e_nascimento(estado, form, erros):
    """Confere o estado (uma das 27 siglas), a data de nascimento (dia, mês e ano) e a idade mínima.
    Devolve a data de nascimento, ou None se estiver errada."""
    if estado not in SIGLAS_ESTADOS:
        erros.append("Escolha o seu estado na lista.")
    dia_texto = form.get("dia_nascimento", "")
    mes_texto = form.get("mes_nascimento", "")
    ano_texto = form.get("ano_nascimento", "")
    if not dia_texto.isdigit() or not mes_texto.isdigit() or not ano_texto.isdigit():
        erros.append("Escolha o dia, o mês e o ano em que você nasceu.")
        return None
    try:
        nascimento = date(int(ano_texto), int(mes_texto), int(dia_texto))
    except ValueError:
        # por exemplo, 31 de abril ou 29 de fevereiro fora de ano bissexto
        erros.append("Essa data de nascimento não existe.")
        return None
    idade = calcular_idade(nascimento, hoje())
    if idade < 0 or idade > IDADE_MAXIMA:
        erros.append("Escolha uma data de nascimento válida.")
        return None
    if idade < IDADE_MINIMA:
        erros.append("É preciso ter ao menos " + str(IDADE_MINIMA) + " anos para criar uma conta.")
        return None
    return nascimento


def cadastro(request):
    categorias = Categoria.objects.all()
    contexto = contexto_nascimento()
    contexto["categorias"] = categorias

    if request.method == "POST":
        form = request.POST
        tipo = form.get("tipo", "contratante")
        username = form.get("username", "").strip().lower()
        nome = form.get("nome", "").strip()
        email = form.get("email", "").strip().lower()
        telefone = form.get("telefone", "").strip()
        estado = form.get("estado", "")
        cidade = form.get("cidade", "").strip()
        categoria = form.get("categoria", "")
        preco = form.get("preco", "").strip()
        senha = form.get("senha", "")
        confirmar = form.get("confirmar", "")

        erros = []
        if len(username) < 3 or not username.replace("_", "").replace(".", "").isalnum():
            erros.append("O usuário precisa ter ao menos 3 caracteres (letras, números, ponto ou _).")
        if len(nome) < 3:
            erros.append("Informe seu nome completo.")
        if "@" not in email:
            erros.append("Informe um e-mail válido.")
        nascimento = validar_estado_e_nascimento(estado, form, erros)
        # a cidade só é pedida ao artista: é ela que a busca usa para achar artistas perto do evento
        if tipo == "artista" and cidade == "":
            erros.append("Informe a cidade onde você se apresenta.")
        if tipo != "artista":
            cidade = ""
        if tipo == "artista" and not categoria.isdigit():
            erros.append("Escolha uma categoria.")
        elif tipo == "artista" and not Categoria.objects.filter(id=categoria).exists():
            erros.append("Escolha uma categoria válida.")

        # o preço é validado ANTES de gravar qualquer coisa no banco
        preco_minimo = 0
        if tipo == "artista" and preco != "":
            try:
                preco_minimo = numero_ou_none(preco)
                if preco_minimo < 0:
                    erros.append("O preço não pode ser negativo.")
            except ValueError:
                erros.append("Informe um preço válido.")

        if len(senha) < 8:
            erros.append("A senha precisa ter ao menos 8 caracteres.")
        if senha != confirmar:
            erros.append("As senhas não coincidem.")
        if form.get("termos") != "on":
            erros.append("É necessário aceitar os termos.")
        if len(erros) == 0 and (User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists()):
            erros.append("Esse usuário ou e-mail já está cadastrado.")

        if len(erros) == 0:
            # tudo junto: o usuário, o perfil e (se for artista) o artista, ou nada
            with transaction.atomic():
                usuario = User.objects.create_user(username=username, email=email, password=senha)
                papel = "cliente"
                if tipo == "artista":
                    papel = "artista"
                Perfil.objects.create(user=usuario, nome=nome, telefone=telefone, cidade=cidade, estado=estado,
                                      data_nascimento=nascimento, papel=papel)
                if tipo == "artista":
                    Artista.objects.create(user=usuario, nome_artistico=nome, categoria_id=categoria,
                                           cidade=cidade, preco_minimo=preco_minimo)
            messages.success(request, "Conta criada com sucesso! Agora é só entrar.")
            return redirect("login")

        for erro in erros:
            messages.error(request, erro)
        contexto["form"] = form
        return render(request, "cadastro.html", contexto, status=400)

    contexto["form"] = request.GET
    return render(request, "cadastro.html", contexto)


# ---------------------------------------------------------------
# Painel do cliente
# ---------------------------------------------------------------
def preparar_contrato(contrato, usuario):
    """Junta no contrato as informações que o card do painel mostra."""
    artista = contrato.artista
    contrato.nome_artistico = artista.nome_artistico
    contrato.estilo = artista.estilo
    contrato.foto_url = artista.foto_url
    contrato.artista_user_id = artista.user_id
    contrato.tipo = contrato.evento.tipo

    primeiro = contrato.pagamentos.order_by("criado_em").first()
    contrato.status_pagamento = primeiro.status if primeiro else None

    avaliacao = Avaliacao.objects.filter(contrato=contrato).first()
    contrato.avaliacao_id = avaliacao.id if avaliacao else None
    contrato.minha_nota = avaliacao.nota if avaliacao else None

    cancelamento = Cancelamento.objects.filter(contrato=contrato).first()
    contrato.cancelado_por = cancelamento.cancelado_por if cancelamento else None
    contrato.valor_reembolso = cancelamento.valor_reembolso if cancelamento else None
    contrato.percentual_reembolso = cancelamento.percentual_reembolso if cancelamento else None

    contrato.total_mensagens = contrato.mensagens.count()
    contrato.mensagens_novas = contrato.mensagens.filter(destinatario=usuario, lida=False).count()
    contrato.texto_novas = str(contrato.mensagens_novas) + " nova"
    if contrato.mensagens_novas > 1:
        contrato.texto_novas = contrato.texto_novas + "s"
    contrato.ja_aconteceu = contrato.data_evento <= hoje()
    contrato.no_futuro = contrato.data_evento >= hoje()
    contrato.pode_cancelar = pode_cancelar(contrato)
    return contrato


@login_required
def painel(request):
    if papel_de(request.user) == "artista":
        return redirect("artista_painel")

    usuario = request.user
    aba = request.GET.get("aba", "visao")

    contratos = []
    for contrato in (Contrato.objects.filter(cliente=usuario).select_related("artista", "evento")
                     .order_by("-data_evento")):
        contratos.append(preparar_contrato(contrato, usuario))

    indicadores = {
        "proximos_eventos": Contrato.objects.filter(cliente=usuario, data_evento__gte=hoje(),
                                                    status__in=["aguardando_pagamento", "valor_retido"]).count(),
        "valor_retido": Pagamento.objects.filter(contrato__cliente=usuario, status="retido")
                                         .aggregate(total=Sum("valor"))["total"] or 0,
        "total_contratado": Contrato.objects.filter(cliente=usuario).exclude(status="cancelado")
                                            .aggregate(total=Sum("valor_total"))["total"] or 0,
        "mensagens_novas": Mensagem.objects.filter(destinatario=usuario, lida=False).count(),
    }

    pedidos = list(PedidoOrcamento.objects.filter(evento__cliente=usuario).select_related("categoria", "evento")
                   .order_by("-criado_em"))
    for pedido in pedidos:
        pedido.tipo = pedido.evento.tipo
        pedido.aceita_respostas = pedido.status in ("aberto", "com_propostas")
        pedido.lista_propostas = list(pedido.propostas.exclude(status="declinada").select_related("artista")
                                      .order_by("valor"))
        for proposta in pedido.lista_propostas:
            proposta.nome_artistico = proposta.artista.nome_artistico
            proposta.texto_sugestao = ""
            if proposta.data_sugerida:
                proposta.texto_sugestao = "sugere " + data_br(proposta.data_sugerida)
                if proposta.horario_sugerido:
                    proposta.texto_sugestao = proposta.texto_sugestao + " às " + proposta.horario_sugerido.strftime("%H:%M")

    # mensagens antigas que não estão ligadas a nenhum contrato
    mensagens = list(Mensagem.objects.filter(contrato__isnull=True)
                     .filter(Q(destinatario=usuario) | Q(remetente=usuario))
                     .select_related("remetente__perfil").order_by("enviada_em"))
    for mensagem in mensagens:
        mensagem.minha = mensagem.remetente_id == usuario.id

    favoritos = []
    for favorito in Favorito.objects.filter(cliente=usuario, artista__ativo=True).order_by("-criado_em"):
        favoritos.append(Artista.objects.com_nota().get(id=favorito.artista_id))

    proximos = []
    conversas = []
    for contrato in contratos:
        if not contrato.ja_aconteceu and contrato.status != "cancelado":
            proximos.append(contrato)
        if contrato.total_mensagens > 0:
            conversas.append(contrato)
    proximos.sort(key=lambda c: c.data_evento)

    contexto = {
        "aba": aba,
        "indicadores": indicadores,
        "contratos": contratos,
        "proximos": proximos,
        "conversas": conversas,
        "pedidos": pedidos,
        "mensagens": mensagens,
        "favoritos": favoritos,
        "primeiro_nome": nome_de(usuario).split(" ")[0],
    }
    return render(request, "painel.html", contexto)


def proposta_do_cliente(request, proposta_id):
    if not id_valido(proposta_id):
        return None
    return (Proposta.objects.select_related("pedido__evento", "pedido__categoria", "artista")
            .filter(id=proposta_id, pedido__evento__cliente=request.user).first())


@login_required
def aceitar_proposta(request, proposta_id):
    if request.method != "POST":
        return redirect(url_com_aba("painel", "pedidos"))
    proposta = proposta_do_cliente(request, proposta_id)
    if proposta is None:
        messages.error(request, "Proposta não encontrada.")
        return redirect(url_com_aba("painel", "pedidos"))
    pedido = proposta.pedido
    if proposta.status != "enviada" or pedido.status not in ("aberto", "com_propostas"):
        messages.error(request, "Essa proposta não pode mais ser aceita.")
        return redirect(url_com_aba("painel", "pedidos"))

    data_final = proposta.data_sugerida or pedido.data_evento
    with transaction.atomic():
        proposta.status = "aceita"
        proposta.save()
        pedido.propostas.filter(status="enviada").exclude(id=proposta.id).update(status="recusada")
        pedido.status = "fechado"
        pedido.save()
        Evento.objects.filter(id=pedido.evento_id).update(data_evento=data_final)
        contrato = Contrato.objects.create(
            evento_id=pedido.evento_id, proposta=proposta, cliente=request.user, artista=proposta.artista,
            descricao=pedido.categoria.nome + " · proposta aceita pelo painel",
            data_evento=data_final, local=pedido.local, valor_total=proposta.valor,
        )
        Pagamento.objects.create(contrato=contrato, valor=contrato.valor_total, status="pendente")
        # a data passa a ficar ocupada na agenda do artista
        Disponibilidade.objects.update_or_create(
            artista=proposta.artista, data=data_final,
            defaults={"status": "ocupado", "observacao": "Contrato ArtConnect"},
        )
    notificar(proposta.artista.user, "contrato",
              nome_de(request.user) + " aceitou sua proposta para " + data_br(data_final) + ".",
              url_com_aba("artista_painel", "agenda"))
    messages.success(request, "Proposta de " + proposta.artista.nome_artistico + " aceita! Agora é só fazer o pagamento.")
    return redirect(url_com_aba("painel", "historico"))


@login_required
def recusar_proposta(request, proposta_id):
    proposta = None
    if request.method == "POST":
        proposta = proposta_do_cliente(request, proposta_id)
    if proposta is None or proposta.status != "enviada":
        messages.error(request, "Essa proposta não pode ser recusada.")
        return redirect(url_com_aba("painel", "pedidos"))
    proposta.status = "recusada"
    proposta.save()
    notificar(proposta.artista.user, "proposta", nome_de(request.user) + " recusou sua proposta.",
              url_com_aba("artista_painel", "propostas"))
    messages.success(request, "Proposta recusada.")
    return redirect(url_com_aba("painel", "pedidos"))


def contrato_do_cliente(request, contrato_id):
    if not id_valido(contrato_id):
        return None
    return Contrato.objects.select_related("artista").filter(id=contrato_id, cliente=request.user).first()


@login_required
def confirmar_evento(request, contrato_id):
    contrato = contrato_do_cliente(request, contrato_id)
    if request.method != "POST" or contrato is None:
        messages.error(request, "Contrato não encontrado.")
    elif contrato.status != "valor_retido":
        messages.error(request, "Só dá para confirmar contratos com pagamento retido.")
    elif contrato.data_evento > hoje():
        messages.error(request, "Você só pode confirmar depois da data do evento.")
    else:
        with transaction.atomic():
            contrato.status = "concluido"
            contrato.save()
            contrato.pagamentos.filter(status="retido").update(status="liberado", liberado_em=timezone.now())
        messages.success(request, "Evento confirmado e pagamento liberado ao artista. Que tal avaliar?")
        return redirect("avaliar_contrato", contrato_id=contrato.id)
    return redirect(url_com_aba("painel", "historico"))


@login_required
def avaliar_contrato(request, contrato_id):
    contrato = contrato_do_cliente(request, contrato_id)
    if contrato is None:
        messages.error(request, "Contrato não encontrado.")
        return redirect(url_com_aba("painel", "historico"))
    if contrato.status != "concluido":
        messages.error(request, "Você só pode avaliar depois que o evento for concluído.")
        return redirect(url_com_aba("painel", "historico"))
    if Avaliacao.objects.filter(contrato=contrato).exists():
        messages.error(request, "Você já avaliou esse serviço.")
        return redirect(url_com_aba("painel", "historico"))

    notas = ["5", "4", "3", "2", "1"]
    if request.method == "POST":
        nota = request.POST.get("nota", "")
        comentario = request.POST.get("comentario", "").strip()
        erros = []
        if nota not in notas:
            erros.append("Escolha uma nota de 1 a 5.")
        if len(comentario) > 500:
            erros.append("O comentário pode ter no máximo 500 caracteres.")
        if len(erros) == 0:
            if comentario == "":
                comentario = None
            try:
                Avaliacao.objects.create(contrato=contrato, artista=contrato.artista, cliente=request.user,
                                         nota=int(nota), comentario=comentario)
                notificar(contrato.artista.user, "avaliacao", "Você recebeu uma avaliação nota " + nota + ".",
                          url_com_aba("artista_painel", "avaliacoes"))
                messages.success(request, "Obrigado pela avaliação! Ela já aparece no perfil de "
                                 + contrato.artista.nome_artistico + ".")
                return redirect("artista_detalhe", artista_id=contrato.artista_id)
            except IntegrityError:
                erros.append("Você já avaliou esse serviço.")
        for erro in erros:
            messages.error(request, erro)
        return render(request, "avaliar.html", {"contrato": contrato, "form": request.POST, "notas": notas}, status=400)

    return render(request, "avaliar.html", {"contrato": contrato, "form": {}, "notas": notas})


# ---------------------------------------------------------------
# Painel do artista
# ---------------------------------------------------------------
@login_required
@artista_obrigatorio
def artista_painel(request):
    artista = artista_logado(request)
    aba = request.GET.get("aba", "pedidos")

    ja_respondidos = Proposta.objects.filter(artista=artista).values_list("pedido_id", flat=True)
    pedidos = list(PedidoOrcamento.objects.filter(categoria=artista.categoria, status__in=["aberto", "com_propostas"],
                                                  data_evento__gte=hoje())
                   .exclude(id__in=ja_respondidos).select_related("evento__cliente__perfil", "categoria")
                   .order_by("data_evento"))
    for pedido in pedidos:
        pedido.tipo = pedido.evento.tipo
        pedido.primeiro_nome = nome_de(pedido.evento.cliente).split(" ")[0]
        pedido.conflito = Disponibilidade.objects.filter(artista=artista, data=pedido.data_evento,
                                                         status="ocupado").exists()

    propostas = list(Proposta.objects.filter(artista=artista).select_related("pedido__evento__cliente__perfil")
                     .order_by("-criado_em"))
    aguardando = 0
    for proposta in propostas:
        proposta.tipo = proposta.pedido.evento.tipo
        proposta.primeiro_nome = nome_de(proposta.pedido.evento.cliente).split(" ")[0]
        if proposta.status == "enviada":
            aguardando = aguardando + 1

    contratos = list(Contrato.objects.filter(artista=artista, data_evento__gte=hoje()).exclude(status="cancelado")
                     .select_related("cliente__perfil", "evento").order_by("data_evento"))
    for contrato in contratos:
        contrato.tipo = contrato.evento.tipo
        contrato.mensagens_novas = contrato.mensagens.filter(destinatario=request.user, lida=False).count()

    contexto = {
        "artista": artista,
        "aba": aba,
        "pedidos": pedidos,
        "propostas": propostas,
        "contratos": contratos,
        "agenda": artista.agenda.filter(data__gte=hoje()).order_by("data"),
        "avaliacoes": artista.avaliacoes.filter(oculta=False).select_related("cliente__perfil").order_by("-criado_em"),
        "portfolio": artista.portfolio.all(),
        "limite_portfolio": LIMITE_PORTFOLIO,
        "aguardando": aguardando,
        "hoje": hoje().isoformat(),
    }
    return render(request, "painel_artista.html", contexto)


@login_required
@artista_obrigatorio
def responder_pedido(request, pedido_id):
    artista = artista_logado(request)
    pedido = None
    if request.method == "POST" and id_valido(pedido_id):
        pedido = (PedidoOrcamento.objects.select_related("evento")
                  .filter(id=pedido_id, categoria=artista.categoria, status__in=["aberto", "com_propostas"]).first())
    if pedido is None:
        messages.error(request, "Pedido não encontrado ou já encerrado.")
        return redirect("artista_painel")
    if Proposta.objects.filter(pedido=pedido, artista_id=artista.id).exists():
        messages.error(request, "Você já respondeu esse pedido.")
        return redirect(url_com_aba("artista_painel", "propostas"))

    acao = request.POST.get("acao", "")
    if acao == "recusar":
        Proposta.objects.create(pedido=pedido, artista_id=artista.id, status="declinada")
        messages.success(request, "Pedido recusado. Ele não vai mais aparecer na sua lista.")
        return redirect("artista_painel")

    erros = []
    valor = None
    try:
        valor = numero_ou_none(request.POST.get("valor", ""))
    except ValueError:
        pass
    if valor is None or valor <= 0:
        erros.append("Informe o valor da proposta.")

    mensagem = request.POST.get("mensagem", "").strip()
    if len(mensagem) > 500:
        erros.append("A mensagem pode ter no máximo 500 caracteres.")

    data_sugerida = None
    horario_sugerido = None
    if acao == "contraproposta":
        data_sugerida = data_ou_none(request.POST.get("data_sugerida", ""))
        if data_sugerida is None:
            erros.append("Informe a nova data da contraproposta.")
        elif data_sugerida < hoje():
            erros.append("A nova data não pode estar no passado.")
        horario = request.POST.get("horario_sugerido", "")
        if horario != "":
            try:
                horario_sugerido = time.fromisoformat(horario)
            except ValueError:
                erros.append("Horário inválido.")
    elif Disponibilidade.objects.filter(artista_id=artista.id, data=pedido.data_evento, status="ocupado").exists():
        erros.append("Sua agenda está ocupada nessa data. Envie uma contraproposta com outra data.")

    if len(erros) > 0:
        for erro in erros:
            messages.error(request, erro)
        return redirect("artista_painel")

    with transaction.atomic():
        Proposta.objects.create(pedido=pedido, artista_id=artista.id, valor=valor, mensagem=mensagem,
                                data_sugerida=data_sugerida, horario_sugerido=horario_sugerido)
        if pedido.status == "aberto":
            pedido.status = "com_propostas"
            pedido.save()
    texto_aviso = artista.nome_artistico + " enviou uma proposta de " + moeda(valor) + "."
    if acao == "contraproposta":
        texto_aviso = artista.nome_artistico + " sugeriu outra data: " + data_br(data_sugerida) + "."
    notificar(pedido.evento.cliente, "proposta", texto_aviso, url_com_aba("painel", "pedidos"))
    if acao == "contraproposta":
        messages.success(request, "Contraproposta enviada! O cliente vai ver a nova data no painel dele.")
    else:
        messages.success(request, "Proposta enviada! Você será avisado quando o cliente responder.")
    return redirect(url_com_aba("artista_painel", "propostas"))


@login_required
@artista_obrigatorio
def atualizar_agenda(request):
    artista = artista_logado(request)
    if request.method != "POST":
        return redirect(url_com_aba("artista_painel", "agenda"))
    acao = request.POST.get("acao", "salvar")
    data_agenda = data_ou_none(request.POST.get("data", ""))
    if data_agenda is None:
        messages.error(request, "Informe uma data válida.")
        return redirect(url_com_aba("artista_painel", "agenda"))

    if acao == "remover":
        Disponibilidade.objects.filter(artista_id=artista.id, data=data_agenda).delete()
        messages.success(request, "Data liberada na agenda.")
        return redirect(url_com_aba("artista_painel", "agenda"))

    status = request.POST.get("status", "ocupado")
    observacao = request.POST.get("observacao", "").strip()
    if data_agenda < hoje():
        messages.error(request, "Escolha uma data a partir de hoje.")
    elif status not in ("ocupado", "disponivel"):
        messages.error(request, "Status inválido.")
    elif len(observacao) > 120:
        messages.error(request, "A observação pode ter no máximo 120 caracteres.")
    else:
        Disponibilidade.objects.update_or_create(artista_id=artista.id, data=data_agenda,
                                                 defaults={"status": status, "observacao": observacao})
        messages.success(request, "Agenda atualizada.")
    return redirect(url_com_aba("artista_painel", "agenda"))


# ---------------------------------------------------------------
# Pedido de orçamento
# ---------------------------------------------------------------
@login_required
def orcamento(request):
    categorias = Categoria.objects.all()
    contexto = {"categorias": categorias, "tipos": TIPOS_EVENTO, "hoje": hoje().isoformat()}

    if request.method == "POST":
        form = request.POST
        erros = []
        data_evento = data_ou_none(form.get("data", ""))
        if data_evento is None:
            erros.append("Informe a data do evento.")
        elif data_evento < hoje():
            erros.append("A data não pode estar no passado.")
        categoria = form.get("categoria", "")
        if not categoria.isdigit() or not Categoria.objects.filter(id=categoria).exists():
            erros.append("Escolha o tipo de serviço.")
        horario = None
        try:
            horario = time.fromisoformat(form.get("horario", ""))
        except ValueError:
            erros.append("Informe o horário de início.")
        if not form.get("duracao", "").isdigit() or int(form.get("duracao")) < 1:
            erros.append("Informe a duração em horas.")
        if not form.get("convidados", "").isdigit() or int(form.get("convidados")) < 1:
            erros.append("Informe a estimativa de convidados.")
        if len(form.get("local", "").strip()) < 5:
            erros.append("Informe o local com pelo menos 5 caracteres.")
        if len(form.get("observacoes", "")) > 600:
            erros.append("As observações podem ter no máximo 600 caracteres.")
        tipo_evento = form.get("tipo_evento", "outro")
        tipos_validos = []
        for codigo, nome in TIPOS_EVENTO:
            tipos_validos.append(codigo)
        if tipo_evento not in tipos_validos:
            tipo_evento = "outro"

        if len(erros) == 0:
            with transaction.atomic():
                evento = Evento.objects.create(cliente=request.user, tipo=tipo_evento, categoria_id=categoria,
                                               data_evento=data_evento, localizacao=form["local"].strip())
                PedidoOrcamento.objects.create(
                    evento=evento, categoria_id=categoria, data_evento=data_evento, horario_inicio=horario,
                    duracao_horas=int(form["duracao"]), estimativa_convidados=int(form["convidados"]),
                    local=form["local"].strip(), observacoes=form.get("observacoes", "").strip(),
                )
            messages.success(request, "Pedido enviado! Você vai receber as propostas no seu painel.")
            return redirect(url_com_aba("painel", "pedidos"))

        for erro in erros:
            messages.error(request, erro)
        contexto["form"] = form
        return render(request, "orcamento.html", contexto, status=400)

    contexto["form"] = request.GET
    return render(request, "orcamento.html", contexto)


# ---------------------------------------------------------------
# Edição e remoção de usuário
# ---------------------------------------------------------------
def perfil_do_usuario(user):
    perfil, criado = Perfil.objects.get_or_create(
        user=user, defaults={"nome": user.username, "papel": papel_de(user) or "cliente"}
    )
    return perfil


@login_required
def editar_perfil(request):
    perfil = perfil_do_usuario(request.user)

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        email = request.POST.get("email", "").strip().lower()
        telefone = request.POST.get("telefone", "").strip()
        estado = request.POST.get("estado", "")
        nova_senha = request.POST.get("nova_senha", "")

        erros = []
        nascimento = validar_estado_e_nascimento(estado, request.POST, erros)
        if len(nome) < 3:
            erros.append("Informe seu nome completo.")
        if "@" not in email:
            erros.append("Informe um e-mail válido.")
        elif User.objects.filter(email=email).exclude(id=request.user.id).exists():
            erros.append("Esse e-mail já está em uso por outra conta.")
        if nova_senha != "" and len(nova_senha) < 8:
            erros.append("A nova senha precisa ter ao menos 8 caracteres.")

        if len(erros) == 0:
            perfil.nome = nome
            perfil.telefone = telefone
            perfil.estado = estado
            perfil.data_nascimento = nascimento
            perfil.save()
            request.user.email = email
            if nova_senha != "":
                request.user.set_password(nova_senha)
            request.user.save()
            if nova_senha != "":
                # trocar a senha encerraria a sessão; isto mantém o usuário logado
                login(request, request.user)
            messages.success(request, "Dados salvos!")
            return redirect("editar_perfil")

        for erro in erros:
            messages.error(request, erro)

    contexto = contexto_nascimento()
    contexto["usuario"] = perfil
    return render(request, "perfil_editar.html", contexto)


@login_required
def excluir_conta(request):
    if request.method == "POST":
        senha = request.POST.get("password", "")
        confirmacao = request.POST.get("confirm_text", "").strip().upper()
        retidos = Pagamento.objects.filter(contrato__cliente=request.user, status="retido").count()

        if not request.user.check_password(senha):
            messages.error(request, "Senha incorreta.")
        elif confirmacao != "EXCLUIR" or request.POST.get("confirm_check") != "on":
            messages.error(request, "Confirme a exclusão digitando EXCLUIR e marcando a caixa.")
        elif retidos > 0:
            messages.error(request, "Você tem contratações com pagamento retido. Finalize-as antes de excluir a conta.")
        else:
            with transaction.atomic():
                Artista.objects.filter(user=request.user).update(ativo=False)
                request.user.delete()
            logout(request)
            messages.success(request, "Sua conta foi excluída.")
            return redirect("index")

    return render(request, "excluir.html")


# ---------------------------------------------------------------
# Administração
# ---------------------------------------------------------------
@login_required
@admin_obrigatorio
def listar_usuarios(request):
    busca = request.GET.get("busca", "").strip()
    papel = request.GET.get("papel", "")

    usuarios = User.objects.select_related("perfil").filter(perfil__isnull=False)
    if busca != "":
        usuarios = usuarios.filter(Q(perfil__nome__icontains=busca) | Q(username__icontains=busca)
                                   | Q(email__icontains=busca))
    if papel in ("cliente", "artista", "admin"):
        usuarios = usuarios.filter(perfil__papel=papel)
    usuarios = usuarios.order_by("-perfil__criado_em")
    return render(request, "usuarios.html", {"usuarios": usuarios, "busca": busca, "papel": papel})


@login_required
@admin_obrigatorio
def admin_dashboard(request):
    contratos_validos = Contrato.objects.exclude(status="cancelado")
    nota = Avaliacao.objects.aggregate(media=Avg("nota"))["media"]
    totais = {
        "clientes": Perfil.objects.filter(papel="cliente").count(),
        "contas_artista": Perfil.objects.filter(papel="artista").count(),
        "artistas_ativos": Artista.objects.filter(ativo=True).count(),
        "novos_30_dias": Perfil.objects.filter(criado_em__gte=timezone.now() - timedelta(days=30)).count(),
        "pedidos": PedidoOrcamento.objects.count(),
        "propostas": Proposta.objects.exclude(status="declinada").count(),
        "contratos": contratos_validos.count(),
        "volume": contratos_validos.aggregate(total=Sum("valor_total"))["total"] or 0,
        "retido": Pagamento.objects.filter(status="retido").aggregate(total=Sum("valor"))["total"] or 0,
        "nota_media": round(nota, 1) if nota is not None else None,
        "avaliacoes": Avaliacao.objects.count(),
        "denuncias_abertas": Denuncia.objects.filter(status="aberta").count(),
        "chamados_abertos": ChamadoSuporte.objects.exclude(status="resolvido").count(),
        "chamados_atrasados": 0,
    }
    for item in ChamadoSuporte.objects.exclude(status="resolvido"):
        if chamado_atrasado(item):
            totais["chamados_atrasados"] = totais["chamados_atrasados"] + 1
    pedidos_por_status = PedidoOrcamento.objects.values("status").annotate(total=Count("id")).order_by("-total")
    contratos_por_status = Contrato.objects.values("status").annotate(total=Count("id")).order_by("-total")

    categorias = []
    for categoria in Categoria.objects.all():
        categoria.pedidos = PedidoOrcamento.objects.filter(categoria=categoria).count()
        categoria.contratos = contratos_validos.filter(artista__categoria=categoria).count()
        categorias.append(categoria)
    categorias.sort(key=lambda c: (-c.pedidos, -c.contratos, c.nome))

    ranking = (Artista.objects.com_nota().filter(total_avaliacoes__gt=0)
               .order_by("-nota_media", "-total_avaliacoes", "nome_artistico")[:5])

    # conversão: quantos pedidos viraram contrato
    fechados = 0
    for linha in pedidos_por_status:
        if linha["status"] == "fechado":
            fechados = linha["total"]
    conversao = 0
    if totais["pedidos"] > 0:
        conversao = round(fechados / totais["pedidos"] * 100)

    maior = 1
    for categoria in categorias:
        if categoria.pedidos + categoria.contratos > maior:
            maior = categoria.pedidos + categoria.contratos
    for categoria in categorias:
        categoria.largura_pedidos = round(categoria.pedidos / maior * 100, 1)
        categoria.largura_contratos = round(categoria.contratos / maior * 100, 1)

    contexto = {
        "totais": totais,
        "listas_status": [("Pedidos por status", pedidos_por_status, False),
                          ("Contratos por status", contratos_por_status, True)],
        "categorias": categorias,
        "ranking": ranking,
        "conversao": conversao,
        "relatorios": RELATORIOS,
    }
    return render(request, "admin.html", contexto)


# ---------------------------------------------------------------
# Sprint 7 · Pagamento simulado (o valor fica retido até o evento)
# ---------------------------------------------------------------
@login_required
def pagar_contrato(request, contrato_id):
    contrato = contrato_do_cliente(request, contrato_id)
    if contrato is None:
        messages.error(request, "Contrato não encontrado.")
        return redirect(url_com_aba("painel", "historico"))
    if contrato.status != "aguardando_pagamento":
        messages.error(request, "Esse contrato não está aguardando pagamento.")
        return redirect(url_com_aba("painel", "historico"))
    if contrato.data_evento < hoje():
        messages.error(request, "A data desse evento já passou. Cancele o contrato ou fale com o artista.")
        return redirect(url_com_aba("painel", "historico"))

    # Sprint 8: cupom de desconto (vem no endereço ao clicar em "Aplicar" e no formulário ao pagar)
    if request.method == "POST":
        codigo = request.POST.get("cupom", "")
    else:
        codigo = request.GET.get("cupom", "")
    codigo = codigo.strip().upper()
    cupom = None
    desconto = 0
    if codigo != "":
        cupom, desconto, erro = validar_cupom(codigo, contrato, request.user)
        if erro:
            messages.error(request, erro)
        elif request.method == "GET":
            messages.success(request, "Cupom " + cupom.codigo + " aplicado: desconto de " + moeda(desconto) + ".")
    contexto = {
        "contrato": contrato,
        "metodos": METODOS_PAGAMENTO,
        "cupom": cupom,
        "codigo_cupom": codigo,
        "desconto": desconto,
        "total_a_pagar": float(contrato.valor_total) - desconto,
    }

    if request.method == "POST":
        metodo = request.POST.get("metodo", "")
        if codigo != "" and cupom is None:
            return render(request, "pagar.html", contexto, status=400)
        if metodo not in ("pix", "boleto"):
            messages.error(request, "Escolha a forma de pagamento.")
            return render(request, "pagar.html", contexto, status=400)
        if request.POST.get("ciente") != "on":
            messages.error(request, "Confirme que leu como funciona a retenção do valor.")
            return render(request, "pagar.html", contexto, status=400)
        with transaction.atomic():
            contrato.pagamentos.filter(status="pendente").update(
                status="retido", metodo=metodo, pago_em=timezone.now(), cupom=cupom, desconto=desconto,
                valor=contexto["total_a_pagar"])
            contrato.status = "valor_retido"
            contrato.save()
        notificar(contrato.artista.user, "pagamento",
                  "Pagamento de " + moeda(contrato.valor_total) + " confirmado para "
                  + data_br(contrato.data_evento) + ". O valor fica retido até o evento.",
                  url_com_aba("artista_painel", "agenda"))
        messages.success(request, "Pagamento confirmado! O valor fica retido e só vai para o artista depois do evento.")
        return redirect(url_com_aba("painel", "pagamentos"))

    return render(request, "pagar.html", contexto)


# ---------------------------------------------------------------
# Sprint 7 · Cancelamento com reembolso (política da Sprint 6)
# ---------------------------------------------------------------
def simular_cancelamento(contrato, cancelado_por):
    """Calcula o reembolso de um contrato sem gravar nada."""
    dias = (contrato.data_evento - hoje()).days
    horas = (timezone.now() - contrato.criado_em).total_seconds() / 3600
    percentual = percentual_reembolso(cancelado_por, dias, horas)
    pagamento = contrato.pagamentos.order_by("criado_em").first()
    valor_pago = 0
    if pagamento is not None and pagamento.status == "retido":
        valor_pago = pagamento.valor
    reembolso, parte_artista = dividir_valor(valor_pago, percentual)
    return {
        "dias": dias,
        "percentual": percentual,
        "pagamento": pagamento,
        "valor_pago": valor_pago,
        "reembolso": reembolso,
        "parte_artista": parte_artista,
    }


def cancelar(contrato, cancelado_por, motivo):
    calculo = simular_cancelamento(contrato, cancelado_por)
    pagamento = calculo["pagamento"]
    with transaction.atomic():
        contrato.status = "cancelado"
        contrato.save()
        Cancelamento.objects.create(contrato=contrato, cancelado_por=cancelado_por, motivo=motivo,
                                    dias_antecedencia=calculo["dias"], percentual_reembolso=calculo["percentual"],
                                    valor_reembolso=calculo["reembolso"], valor_artista=calculo["parte_artista"])
        # a data volta a ficar livre na agenda do artista
        Disponibilidade.objects.filter(artista_id=contrato.artista_id, data=contrato.data_evento,
                                       observacao="Contrato ArtConnect").delete()
        if pagamento is not None and pagamento.status == "pendente":
            # nada foi pago: o pagamento pendente deixa de existir
            pagamento.delete()
        elif pagamento is not None and pagamento.status == "retido":
            if calculo["parte_artista"] == 0:
                pagamento.status = "reembolsado"
                pagamento.save()
            elif calculo["reembolso"] == 0:
                pagamento.status = "liberado"
                pagamento.liberado_em = timezone.now()
                pagamento.save()
            else:
                # reembolso parcial: o pagamento se divide em duas linhas
                pagamento.status = "reembolsado"
                pagamento.valor = calculo["reembolso"]
                pagamento.save()
                Pagamento.objects.create(contrato=contrato, valor=calculo["parte_artista"], metodo=pagamento.metodo,
                                         status="liberado", pago_em=pagamento.pago_em, liberado_em=timezone.now())
        if cancelado_por == "artista" and contrato.proposta_id is not None:
            # o pedido volta a ficar aberto para outros artistas da categoria
            PedidoOrcamento.objects.filter(propostas__id=contrato.proposta_id, status="fechado",
                                           data_evento__gte=hoje()).update(status="aberto")
    return calculo


def pode_cancelar(contrato):
    return contrato.status in ("aguardando_pagamento", "valor_retido") and contrato.data_evento >= hoje()


@login_required
def cancelar_contrato(request, contrato_id):
    contrato = contrato_do_cliente(request, contrato_id)
    if contrato is None or not pode_cancelar(contrato):
        messages.error(request, "Esse contrato não pode ser cancelado.")
        return redirect(url_com_aba("painel", "historico"))

    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if len(motivo) < 5 or len(motivo) > 300:
            messages.error(request, "Conte o motivo do cancelamento (5 a 300 caracteres).")
        elif request.POST.get("confirmo") != "on":
            messages.error(request, "Marque a caixa confirmando que leu as regras de reembolso.")
        else:
            calculo = cancelar(contrato, "cliente", motivo)
            notificar(contrato.artista.user, "cancelamento",
                      nome_de(request.user) + " cancelou o evento de " + data_br(contrato.data_evento)
                      + ". Sua parte: " + moeda(calculo["parte_artista"]) + ".",
                      url_com_aba("artista_painel", "agenda"))
            messages.success(request, "Contrato cancelado. Reembolso de " + moeda(calculo["reembolso"]) + " ("
                             + str(calculo["percentual"]) + "% do valor pago).")
            return redirect(url_com_aba("painel", "historico"))
        contexto = {"contrato": contrato, "calculo": simular_cancelamento(contrato, "cliente"), "faixas": FAIXAS_REEMBOLSO}
        return render(request, "cancelar.html", contexto, status=400)

    contexto = {"contrato": contrato, "calculo": simular_cancelamento(contrato, "cliente"), "faixas": FAIXAS_REEMBOLSO}
    return render(request, "cancelar.html", contexto)


@login_required
@artista_obrigatorio
def artista_cancelar_contrato(request, contrato_id):
    artista = artista_logado(request)
    contrato = None
    if request.method == "POST" and id_valido(contrato_id):
        contrato = Contrato.objects.filter(id=contrato_id, artista_id=artista.id).first()
    motivo = request.POST.get("motivo", "").strip()
    if contrato is None or not pode_cancelar(contrato):
        messages.error(request, "Esse contrato não pode ser cancelado.")
    elif len(motivo) < 5 or len(motivo) > 300:
        messages.error(request, "Conte ao cliente o motivo do cancelamento (5 a 300 caracteres).")
    else:
        calculo = cancelar(contrato, "artista", motivo)
        notificar(contrato.cliente, "cancelamento",
                  artista.nome_artistico + " cancelou o evento de " + data_br(contrato.data_evento)
                  + ". Você recebe 100% de volta.", url_com_aba("painel", "historico"))
        anteriores = Cancelamento.objects.filter(contrato__artista_id=artista.id, cancelado_por="artista",
                                                 criado_em__gte=timezone.now() - timedelta(days=365)).count()
        messages.success(request, "Contrato cancelado e cliente reembolsado em " + moeda(calculo["reembolso"]) + ".")
        if anteriores >= 2:
            messages.error(request, "Atenção: este é o seu cancelamento nº " + str(anteriores)
                           + " em 12 meses. Pela política, o perfil pode ser suspenso por 30 dias.")
        else:
            messages.error(request, "Advertência: cancelamentos pelo artista contam para a política de suspensão.")
    return redirect(url_com_aba("artista_painel", "agenda"))


# ---------------------------------------------------------------
# Sprint 7 · Artistas favoritos
# ---------------------------------------------------------------
@login_required
def alternar_favorito(request, artista_id):
    if papel_de(request.user) != "cliente":
        messages.error(request, "Só clientes podem salvar artistas favoritos.")
        return redirect("index")
    artista = None
    if request.method == "POST" and id_valido(artista_id):
        artista = Artista.objects.filter(id=artista_id, ativo=True).first()
    if artista is None:
        messages.error(request, "Artista não encontrado.")
        return redirect("index")

    favorito = Favorito.objects.filter(cliente=request.user, artista=artista).first()
    if favorito is None:
        Favorito.objects.get_or_create(cliente=request.user, artista=artista)
        messages.success(request, artista.nome_artistico + " foi salvo nos seus favoritos.")
    else:
        favorito.delete()
        messages.success(request, artista.nome_artistico + " saiu dos seus favoritos.")

    voltar = request.POST.get("voltar", "")
    if link_interno(voltar):
        return redirect(voltar)
    return redirect("artista_detalhe", artista_id=artista.id)


# ---------------------------------------------------------------
# Sprint 7 · Central de notificações
# ---------------------------------------------------------------
@login_required
def notificacoes(request):
    lista = Notificacao.objects.filter(user=request.user).order_by("-criada_em")[:50]
    return render(request, "notificacoes.html", {"notificacoes": lista})


@login_required
def abrir_notificacao(request, notificacao_id):
    aviso = None
    if request.method == "POST" and id_valido(notificacao_id):
        aviso = Notificacao.objects.filter(id=notificacao_id, user=request.user).first()
    if aviso is None:
        messages.error(request, "Notificação não encontrada.")
        return redirect("notificacoes")
    aviso.lida = True
    aviso.save()
    if link_interno(aviso.link):
        return redirect(aviso.link)
    return redirect("notificacoes")


@login_required
def ler_todas_notificacoes(request):
    if request.method == "POST":
        Notificacao.objects.filter(user=request.user, lida=False).update(lida=True)
        messages.success(request, "Todas as notificações foram marcadas como lidas.")
    return redirect("notificacoes")


# ---------------------------------------------------------------
# Sprint 7 · Conversa entre cliente e artista dentro do contrato
# ---------------------------------------------------------------
def contrato_da_conversa(request, contrato_id):
    """Contrato que o usuário logado pode ver: ele é o cliente ou o artista."""
    if not id_valido(contrato_id):
        return None
    return (Contrato.objects.select_related("artista", "cliente__perfil")
            .filter(Q(cliente=request.user) | Q(artista__user=request.user), id=contrato_id).first())


@login_required
def conversa(request, contrato_id):
    contrato = contrato_da_conversa(request, contrato_id)
    if contrato is None:
        messages.error(request, "Conversa não encontrada.")
        return redirect(destino_painel(request))

    sou_cliente = contrato.cliente_id == request.user.id
    if sou_cliente:
        outro = contrato.artista.user
    else:
        outro = contrato.cliente

    if request.method == "POST":
        conteudo = request.POST.get("conteudo", "").strip()
        if outro is None:
            messages.error(request, "Esse artista ainda não tem conta na plataforma para responder mensagens.")
        elif contrato.status == "cancelado":
            messages.error(request, "Não dá para enviar mensagens em um contrato cancelado.")
        elif conteudo == "" or len(conteudo) > 1000:
            messages.error(request, "Escreva uma mensagem de até 1000 caracteres.")
        else:
            Mensagem.objects.create(contrato=contrato, remetente=request.user, destinatario=outro, conteudo=conteudo)
            notificar(outro, "mensagem", nome_de(request.user) + ": " + conteudo[:120],
                      reverse("conversa", args=[contrato.id]))
        return redirect(reverse("conversa", args=[contrato.id]) + "#fim")

    # abrir a conversa marca como lidas as mensagens recebidas
    contrato.mensagens.filter(destinatario=request.user, lida=False).update(lida=True)
    mensagens = list(contrato.mensagens.select_related("remetente__perfil").order_by("enviada_em"))
    for mensagem in mensagens:
        mensagem.minha = mensagem.remetente_id == request.user.id
    contexto = {
        "contrato": contrato,
        "mensagens": mensagens,
        "sou_cliente": sou_cliente,
        "pode_responder": outro is not None and contrato.status != "cancelado",
    }
    return render(request, "conversa.html", contexto)


# ---------------------------------------------------------------
# Sprint 7 · Denúncias e moderação
# ---------------------------------------------------------------
@login_required
def denunciar(request):
    if request.method != "POST":
        return redirect("index")
    alvo = request.POST.get("alvo", "")
    alvo_id = request.POST.get("alvo_id", "")
    motivo = request.POST.get("motivo", "")
    detalhes = request.POST.get("detalhes", "").strip()

    artista = None
    avaliacao = None
    if id_valido(alvo_id) and alvo == "artista":
        artista = Artista.objects.filter(id=alvo_id).first()
    elif id_valido(alvo_id) and alvo == "avaliacao":
        avaliacao = Avaliacao.objects.filter(id=alvo_id).first()
    if artista is None and avaliacao is None:
        messages.error(request, "Conteúdo não encontrado.")
        return redirect("index")
    if artista is not None:
        voltar = artista.id
    else:
        voltar = avaliacao.artista_id

    codigos = []
    for item in MOTIVOS_DENUNCIA:
        codigos.append(item[0])
    if motivo not in codigos:
        messages.error(request, "Escolha o motivo da denúncia.")
    elif len(detalhes) > 500:
        messages.error(request, "Os detalhes podem ter no máximo 500 caracteres.")
    else:
        try:
            with transaction.atomic():
                Denuncia.objects.create(denunciante=request.user, artista=artista, avaliacao=avaliacao,
                                        motivo=motivo, detalhes=detalhes)
            messages.success(request, "Denúncia enviada. A equipe analisa em até 48 horas e você recebe "
                             "a resposta nas notificações.")
        except IntegrityError:
            messages.error(request, "Você já denunciou esse conteúdo e a análise ainda está aberta.")
    return redirect("artista_detalhe", artista_id=voltar)


@login_required
@admin_obrigatorio
def admin_denuncias(request):
    filtro = request.GET.get("status", "aberta")
    if filtro not in ("aberta", "procedente", "improcedente"):
        filtro = "aberta"
    denuncias = list(Denuncia.objects.filter(status=filtro)
                     .select_related("denunciante__perfil", "artista", "avaliacao__artista", "avaliacao__cliente__perfil")
                     .order_by("criada_em"))
    for denuncia in denuncias:
        # artista do perfil denunciado ou da avaliação denunciada
        if denuncia.artista is not None:
            denuncia.artista_ref = denuncia.artista
        else:
            denuncia.artista_ref = denuncia.avaliacao.artista
    totais = {"aberta": 0, "procedente": 0, "improcedente": 0}
    for linha in Denuncia.objects.values("status").annotate(total=Count("id")):
        totais[linha["status"]] = linha["total"]
    return render(request, "denuncias.html", {"denuncias": denuncias, "filtro": filtro, "totais": totais})


@login_required
@admin_obrigatorio
def decidir_denuncia(request, denuncia_id):
    denuncia = None
    if request.method == "POST" and id_valido(denuncia_id):
        denuncia = Denuncia.objects.filter(id=denuncia_id, status="aberta").first()
    if denuncia is None:
        messages.error(request, "Denúncia não encontrada ou já decidida.")
        return redirect("admin_denuncias")

    decisao = request.POST.get("decisao", "")
    justificativa = request.POST.get("justificativa", "").strip()
    if decisao not in ("procedente", "improcedente"):
        messages.error(request, "Escolha uma decisão.")
        return redirect("admin_denuncias")
    if len(justificativa) < 5 or len(justificativa) > 300:
        messages.error(request, "Escreva a justificativa da decisão (5 a 300 caracteres).")
        return redirect("admin_denuncias")

    agora = timezone.now()
    with transaction.atomic():
        denuncia.status = decisao
        denuncia.decisao = justificativa
        denuncia.resolvida_em = agora
        denuncia.save()
        if decisao == "procedente":
            if denuncia.avaliacao_id is not None:
                Avaliacao.objects.filter(id=denuncia.avaliacao_id).update(oculta=True)
                # outras denúncias abertas sobre a mesma avaliação são resolvidas junto
                Denuncia.objects.filter(avaliacao_id=denuncia.avaliacao_id, status="aberta").update(
                    status="procedente", decisao=justificativa, resolvida_em=agora)
            else:
                Artista.objects.filter(id=denuncia.artista_id).update(ativo=False)
                Denuncia.objects.filter(artista_id=denuncia.artista_id, status="aberta").update(
                    status="procedente", decisao=justificativa, resolvida_em=agora)

    texto = "Sua denúncia foi analisada: "
    if decisao == "procedente":
        texto = texto + "o conteúdo foi removido. Obrigado por ajudar!"
    else:
        texto = texto + "não encontramos violação das regras."
    notificar(denuncia.denunciante, "moderacao", texto, reverse("notificacoes"))
    if decisao == "procedente" and denuncia.artista_id is not None:
        notificar(denuncia.artista.user, "moderacao", "Seu perfil foi suspenso pela moderação: " + justificativa,
                  reverse("artista_painel"))
    messages.success(request, "Decisão registrada.")
    return redirect("admin_denuncias")


@login_required
@admin_obrigatorio
def reativar_artista(request, artista_id):
    if request.method == "POST" and id_valido(artista_id):
        artista = Artista.objects.filter(id=artista_id).first()
        if artista is not None:
            artista.ativo = True
            artista.save()
            notificar(artista.user, "moderacao", "Seu perfil foi reativado e voltou para a busca.",
                      reverse("artista_painel"))
            messages.success(request, "Perfil reativado.")
    return redirect(reverse("admin_denuncias") + "?status=procedente")


# ---------------------------------------------------------------
# Sprint 7 · Portfólio do artista
# ---------------------------------------------------------------
@login_required
@artista_obrigatorio
def adicionar_portfolio(request):
    artista = artista_logado(request)
    if request.method != "POST":
        return redirect(url_com_aba("artista_painel", "portfolio"))
    tipo = request.POST.get("tipo", "")
    titulo = request.POST.get("titulo", "").strip()
    url = request.POST.get("url", "").strip()

    erros = []
    if tipo not in ("foto", "video", "audio"):
        erros.append("Escolha o tipo do item.")
    if len(titulo) < 3 or len(titulo) > 80:
        erros.append("O título precisa ter de 3 a 80 caracteres.")
    if not url.startswith("https://") or len(url) > 500 or " " in url:
        erros.append("Cole um link completo começando com https://")
    elif tipo == "video" and link_embed(url) == "":
        erros.append("Para vídeo, use um link do YouTube ou do Vimeo.")
    if Portfolio.objects.filter(artista_id=artista.id).count() >= LIMITE_PORTFOLIO:
        erros.append("O portfólio aceita até " + str(LIMITE_PORTFOLIO) + " itens. Remova um para adicionar outro.")

    if len(erros) == 0:
        Portfolio.objects.create(artista_id=artista.id, tipo=tipo, titulo=titulo, url=url)
        messages.success(request, "Item adicionado ao portfólio. Ele já aparece no seu perfil.")
    for erro in erros:
        messages.error(request, erro)
    return redirect(url_com_aba("artista_painel", "portfolio"))


@login_required
@artista_obrigatorio
def remover_portfolio(request, item_id):
    artista = artista_logado(request)
    if request.method == "POST" and id_valido(item_id):
        Portfolio.objects.filter(id=item_id, artista_id=artista.id).delete()
        messages.success(request, "Item removido do portfólio.")
    return redirect(url_com_aba("artista_painel", "portfolio"))


def pagina_nao_encontrada(request, exception):
    return render(request, "404.html", status=404)


# ---------------------------------------------------------------
# Sprint 8 · Cupom de desconto no pagamento
# ---------------------------------------------------------------
def validar_cupom(codigo, contrato, usuario):
    """Devolve (cupom, desconto em reais, mensagem de erro ou "")."""
    cupom = Cupom.objects.filter(codigo=codigo).first()
    if cupom is None or not cupom.ativo:
        return None, 0, "Cupom " + codigo + " não existe ou não está mais ativo."
    if cupom.validade is not None and cupom.validade < hoje():
        return None, 0, "O cupom " + cupom.codigo + " venceu em " + data_br(cupom.validade) + "."
    usos = Pagamento.objects.filter(cupom=cupom).exclude(pago_em=None).count()
    if cupom.limite_usos is not None and usos >= cupom.limite_usos:
        return None, 0, "O cupom " + cupom.codigo + " já atingiu o limite de usos."
    if Pagamento.objects.filter(cupom=cupom, contrato__cliente=usuario).exclude(contrato=contrato).exists():
        return None, 0, "Você já usou o cupom " + cupom.codigo + " em outra contratação."
    if contrato.valor_total < cupom.valor_minimo:
        return None, 0, "O cupom " + cupom.codigo + " vale para contratos a partir de " + moeda(cupom.valor_minimo) + "."
    desconto = calcular_desconto(cupom.tipo, cupom.valor, contrato.valor_total, cupom.desconto_maximo)
    return cupom, desconto, ""


# ---------------------------------------------------------------
# Sprint 8 · Central de suporte
# ---------------------------------------------------------------
def chamado_atrasado(chamado):
    """Sem resposta da equipe depois do prazo da categoria."""
    if chamado.status == "resolvido" or chamado.prazo_resposta is None:
        return False
    respondeu = chamado.mensagens.filter(da_equipe=True).exists()
    return not respondeu and timezone.now() > chamado.prazo_resposta


@login_required
def suporte(request):
    contratos = Contrato.objects.filter(Q(cliente=request.user) | Q(artista__user=request.user)).select_related("artista")
    form = {}
    if request.method == "POST":
        form = request.POST
        categoria = request.POST.get("categoria", "")
        assunto = request.POST.get("assunto", "").strip()
        descricao = request.POST.get("descricao", "").strip()
        contrato_id = request.POST.get("contrato", "")
        erros = []
        codigos = []
        for codigo, nome in CATEGORIAS_SUPORTE:
            codigos.append(codigo)
        if categoria not in codigos:
            erros.append("Escolha a categoria do problema.")
        if len(assunto) < 5 or len(assunto) > 120:
            erros.append("O assunto precisa ter de 5 a 120 caracteres.")
        if len(descricao) < 10 or len(descricao) > 1000:
            erros.append("Descreva o problema (10 a 1000 caracteres).")
        contrato = None
        if contrato_id != "":
            if id_valido(contrato_id):
                contrato = contratos.filter(id=contrato_id).first()
            if contrato is None:
                erros.append("Contrato não encontrado.")
        if len(erros) == 0:
            chamado = ChamadoSuporte.objects.create(
                user=request.user, categoria=categoria, contrato=contrato, assunto=assunto, descricao=descricao,
                prazo_resposta=timezone.now() + timedelta(hours=PRAZOS_SUPORTE[categoria]),
            )
            messages.success(request, "Chamado aberto! A equipe responde em até "
                             + str(PRAZOS_SUPORTE[categoria]) + " horas.")
            return redirect("chamado", chamado_id=chamado.id)
        for erro in erros:
            messages.error(request, erro)

    chamados = list(ChamadoSuporte.objects.filter(user=request.user).order_by("-criado_em"))
    for chamado in chamados:
        chamado.atrasado = chamado_atrasado(chamado)
    contexto = {
        "chamados": chamados,
        "categorias": CATEGORIAS_SUPORTE,
        "prazos": PRAZOS_SUPORTE,
        "contratos": contratos.order_by("-data_evento"),
        "form": form,
    }
    return render(request, "suporte.html", contexto, status=400 if request.method == "POST" else 200)


@login_required
def chamado(request, chamado_id):
    sou_equipe = papel_de(request.user) == "admin"
    item = None
    if id_valido(chamado_id):
        item = ChamadoSuporte.objects.select_related("user__perfil", "contrato__artista").filter(id=chamado_id).first()
    if item is not None and not sou_equipe and item.user_id != request.user.id:
        item = None
    if item is None:
        messages.error(request, "Chamado não encontrado.")
        return redirect("suporte")

    if request.method == "POST":
        acao = request.POST.get("acao", "responder")
        if acao == "resolver":
            item.status = "resolvido"
            item.save()
            if sou_equipe and item.user_id != request.user.id:
                notificar(item.user, "suporte", "Seu chamado \"" + item.assunto[:60] + "\" foi resolvido.",
                          reverse("chamado", args=[item.id]))
            messages.success(request, "Chamado marcado como resolvido.")
            return redirect("chamado", chamado_id=item.id)
        texto = request.POST.get("texto", "").strip()
        if texto == "" or len(texto) > 1000:
            messages.error(request, "Escreva uma mensagem de até 1000 caracteres.")
        else:
            MensagemChamado.objects.create(chamado=item, autor=request.user, da_equipe=sou_equipe, texto=texto)
            if sou_equipe:
                item.status = "em_andamento"
                notificar(item.user, "suporte", "A equipe respondeu: " + texto[:120], reverse("chamado", args=[item.id]))
            elif item.status == "resolvido":
                item.status = "aberto"   # o usuário voltou a escrever: o chamado reabre
            item.save()
        return redirect(reverse("chamado", args=[item.id]) + "#fim")

    mensagens = list(item.mensagens.select_related("autor__perfil"))
    for mensagem in mensagens:
        mensagem.minha = mensagem.autor_id == request.user.id
    item.atrasado = chamado_atrasado(item)
    return render(request, "chamado.html", {"chamado": item, "mensagens": mensagens, "sou_equipe": sou_equipe})


@login_required
@admin_obrigatorio
def admin_suporte(request):
    filtro = request.GET.get("status", "aberto")
    if filtro not in ("aberto", "em_andamento", "resolvido"):
        filtro = "aberto"
    chamados = list(ChamadoSuporte.objects.filter(status=filtro).select_related("user__perfil")
                    .order_by("prazo_resposta"))
    for item in chamados:
        item.atrasado = chamado_atrasado(item)
    totais = {"aberto": 0, "em_andamento": 0, "resolvido": 0}
    for linha in ChamadoSuporte.objects.values("status").annotate(total=Count("id")):
        totais[linha["status"]] = linha["total"]
    return render(request, "admin_suporte.html", {"chamados": chamados, "filtro": filtro, "totais": totais})


# ---------------------------------------------------------------
# Sprint 8 · Resposta do artista às avaliações
# ---------------------------------------------------------------
@login_required
@artista_obrigatorio
def responder_avaliacao(request, avaliacao_id):
    artista = artista_logado(request)
    avaliacao = None
    if request.method == "POST" and id_valido(avaliacao_id):
        avaliacao = Avaliacao.objects.filter(id=avaliacao_id, artista_id=artista.id, oculta=False).first()
    if avaliacao is None:
        messages.error(request, "Avaliação não encontrada.")
        return redirect(url_com_aba("artista_painel", "avaliacoes"))
    resposta = request.POST.get("resposta", "").strip()
    if len(resposta) < 5 or len(resposta) > 500:
        messages.error(request, "A resposta precisa ter de 5 a 500 caracteres.")
        return redirect(url_com_aba("artista_painel", "avaliacoes"))
    primeira_vez = avaliacao.resposta == ""
    avaliacao.resposta = resposta
    avaliacao.respondida_em = timezone.now()
    avaliacao.save()
    if primeira_vez:
        notificar(avaliacao.cliente, "avaliacao", artista.nome_artistico + " respondeu à sua avaliação.",
                  reverse("artista_detalhe", args=[artista.id]))
    messages.success(request, "Resposta publicada. Ela aparece embaixo da avaliação no seu perfil.")
    return redirect(url_com_aba("artista_painel", "avaliacoes"))


# ---------------------------------------------------------------
# Sprint 8 · Relatórios em CSV para o administrador
# ---------------------------------------------------------------
RELATORIOS = [
    ("contratos", "Contratos"),
    ("pagamentos", "Pagamentos"),
    ("pedidos", "Pedidos de orçamento"),
    ("usuarios", "Usuários"),
    ("chamados", "Chamados de suporte"),
]


def linhas_do_relatorio(tipo):
    """Cabeçalho e linhas de cada relatório."""
    linhas = []
    if tipo == "contratos":
        cabecalho = ["codigo", "cliente", "artista", "categoria", "data_evento", "local", "valor_total", "status", "criado_em"]
        for c in Contrato.objects.select_related("cliente__perfil", "artista__categoria").order_by("-data_evento"):
            linhas.append([str(c.id)[:8], nome_de(c.cliente), c.artista.nome_artistico, c.artista.categoria.nome,
                           data_br(c.data_evento), c.local, str(c.valor_total), c.get_status_display(),
                           data_br(c.criado_em)])
    elif tipo == "pagamentos":
        cabecalho = ["contrato", "artista", "valor_pago", "desconto", "cupom", "metodo", "status", "pago_em", "liberado_em"]
        for pg in Pagamento.objects.select_related("contrato__artista", "cupom").order_by("criado_em"):
            linhas.append([str(pg.contrato_id)[:8], pg.contrato.artista.nome_artistico, str(pg.valor), str(pg.desconto),
                           pg.cupom.codigo if pg.cupom else "", pg.metodo, pg.get_status_display(),
                           data_br(pg.pago_em) if pg.pago_em else "", data_br(pg.liberado_em) if pg.liberado_em else ""])
    elif tipo == "pedidos":
        cabecalho = ["cliente", "categoria", "data_evento", "convidados", "local", "status", "propostas", "criado_em"]
        for p in PedidoOrcamento.objects.select_related("evento__cliente__perfil", "categoria").order_by("-criado_em"):
            linhas.append([nome_de(p.evento.cliente), p.categoria.nome, data_br(p.data_evento), str(p.estimativa_convidados),
                           p.local, p.get_status_display(), str(p.propostas.exclude(status="declinada").count()),
                           data_br(p.criado_em)])
    elif tipo == "usuarios":
        cabecalho = ["usuario", "nome", "email", "cidade", "tipo", "desde"]
        for u in User.objects.select_related("perfil").filter(perfil__isnull=False).order_by("perfil__criado_em"):
            linhas.append([u.username, u.perfil.nome, u.email, u.perfil.cidade, u.perfil.get_papel_display(),
                           data_br(u.perfil.criado_em)])
    else:
        cabecalho = ["assunto", "categoria", "usuario", "status", "aberto_em", "prazo", "respostas_da_equipe"]
        for ch in ChamadoSuporte.objects.select_related("user").order_by("-criado_em"):
            linhas.append([ch.assunto, ch.get_categoria_display(), ch.user.username, ch.get_status_display(),
                           data_br(ch.criado_em), data_br(ch.prazo_resposta) if ch.prazo_resposta else "",
                           str(ch.mensagens.filter(da_equipe=True).count())])
    return cabecalho, linhas


@login_required
@admin_obrigatorio
def exportar_relatorio(request, tipo):
    tipos = []
    for codigo, nome in RELATORIOS:
        tipos.append(codigo)
    if tipo not in tipos:
        messages.error(request, "Relatório não encontrado.")
        return redirect("admin_dashboard")
    cabecalho, linhas = linhas_do_relatorio(tipo)
    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = 'attachment; filename="artconnect-' + tipo + "-" + hoje().isoformat() + '.csv"'
    resposta.write("﻿")   # faz o Excel abrir os acentos certinho
    escritor = csv.writer(resposta, delimiter=";")
    escritor.writerow(cabecalho)
    for linha in linhas:
        escritor.writerow(linha)
    return resposta


# ---------------------------------------------------------------
# Sprint 8 · Comprovante de contratação para impressão
# ---------------------------------------------------------------
@login_required
def comprovante(request, contrato_id):
    contrato = None
    if id_valido(contrato_id):
        contrato = (Contrato.objects.select_related("cliente__perfil", "artista__categoria", "evento", "proposta__pedido")
                    .filter(id=contrato_id).first())
    if contrato is not None:
        pode_ver = (contrato.cliente_id == request.user.id or contrato.artista.user_id == request.user.id
                    or papel_de(request.user) == "admin")
        if not pode_ver:
            contrato = None
    if contrato is None:
        messages.error(request, "Contrato não encontrado.")
        return redirect(destino_painel(request))

    pagamentos = list(contrato.pagamentos.select_related("cupom").order_by("criado_em"))
    desconto = 0
    for pagamento in pagamentos:
        desconto = desconto + float(pagamento.desconto)
    cancelamento = Cancelamento.objects.filter(contrato=contrato).first()
    # código curto para conferir o comprovante (não dá para adivinhar sem saber o contrato)
    verificacao = hashlib.sha256((str(contrato.id) + settings.SECRET_KEY).encode("utf-8")).hexdigest()[:10].upper()
    contexto = {
        "contrato": contrato,
        "pagamentos": pagamentos,
        "desconto": desconto,
        "cancelamento": cancelamento,
        "verificacao": verificacao,
        "emitido_em": timezone.localtime(),
        "horario": contrato.proposta.pedido.horario_inicio if contrato.proposta else None,
    }
    return render(request, "comprovante.html", contexto)
