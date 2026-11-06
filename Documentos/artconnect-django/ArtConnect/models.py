import uuid

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg, Count, Q
from django.db.models.functions import Round
from django.utils import timezone

# ---------------------------------------------------------------
# Opções (choices) usadas nos campos
# ---------------------------------------------------------------
PAPEIS = [
    ("cliente", "Cliente"),
    ("artista", "Artista"),
    ("admin", "Administrador"),
]

# Os 27 estados do Brasil (sigla, nome), na ordem alfabética do nome
ESTADOS = [
    ("AC", "Acre"), ("AL", "Alagoas"), ("AP", "Amapá"), ("AM", "Amazonas"), ("BA", "Bahia"),
    ("CE", "Ceará"), ("DF", "Distrito Federal"), ("ES", "Espírito Santo"), ("GO", "Goiás"),
    ("MA", "Maranhão"), ("MT", "Mato Grosso"), ("MS", "Mato Grosso do Sul"), ("MG", "Minas Gerais"),
    ("PA", "Pará"), ("PB", "Paraíba"), ("PR", "Paraná"), ("PE", "Pernambuco"), ("PI", "Piauí"),
    ("RJ", "Rio de Janeiro"), ("RN", "Rio Grande do Norte"), ("RS", "Rio Grande do Sul"),
    ("RO", "Rondônia"), ("RR", "Roraima"), ("SC", "Santa Catarina"), ("SP", "São Paulo"),
    ("SE", "Sergipe"), ("TO", "Tocantins"),
]
SIGLAS_ESTADOS = [sigla for sigla, nome in ESTADOS]

# idade mínima para ter conta: a plataforma tem contratos e pagamentos
IDADE_MINIMA = 18
IDADE_MAXIMA = 120

MESES = [
    (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"), (5, "Maio"), (6, "Junho"),
    (7, "Julho"), (8, "Agosto"), (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro"),
]


def calcular_idade(ano, mes, hoje):
    """Idade em anos a partir do mês e do ano de nascimento.
    Sem o dia, a pessoa conta como aniversariante a partir do primeiro dia do mês em que nasceu."""
    idade = hoje.year - ano
    if hoje.month < mes:
        idade = idade - 1
    return idade

TIPOS_EVENTO = [
    ("casamento", "Casamento"),
    ("corporativo", "Corporativo"),
    ("aniversario", "Aniversário"),
    ("formatura", "Formatura"),
    ("outro", "Outro"),
]

STATUS_ORCAMENTO = [
    ("aberto", "Aberto"),
    ("com_propostas", "Com propostas"),
    ("fechado", "Fechado"),
    ("cancelado", "Cancelado"),
]

# enviada/aceita/recusada: decisão do cliente; declinada: o artista recusou o pedido
STATUS_PROPOSTA = [
    ("enviada", "Aguardando cliente"),
    ("aceita", "Aceita"),
    ("recusada", "Recusada pelo cliente"),
    ("declinada", "Você recusou"),
]

STATUS_CONTRATO = [
    ("aguardando_pagamento", "Aguardando pagamento"),
    ("valor_retido", "Confirmado"),
    ("concluido", "Concluído"),
    ("cancelado", "Cancelado"),
]

STATUS_PAGAMENTO = [
    ("pendente", "Aguardando pagamento"),
    ("retido", "Valor retido"),
    ("liberado", "Pago ao artista"),
    ("reembolsado", "Reembolsado"),
]

CATEGORIAS_SUPORTE = [
    ("pagamento", "Pagamento ou reembolso"),
    ("contrato", "Problema com um contrato"),
    ("conta", "Conta e acesso"),
    ("tecnico", "Erro no site"),
    ("duvida", "Dúvida geral"),
]

# horas para a primeira resposta da equipe (documento "Categorias e prazos de atendimento do suporte")
PRAZOS_SUPORTE = {
    "pagamento": 24,
    "contrato": 24,
    "conta": 48,
    "tecnico": 48,
    "duvida": 72,
}

TIPOS_CUPOM = [
    ("percentual", "Percentual (%)"),
    ("fixo", "Valor fixo (R$)"),
]

STATUS_SUPORTE = [
    ("aberto", "Aberto"),
    ("em_andamento", "Em andamento"),
    ("resolvido", "Resolvido"),
]

STATUS_AGENDA = [
    ("disponivel", "Disponível"),
    ("ocupado", "Ocupado"),
]

TIPOS_NOTIFICACAO = [
    ("proposta", "Proposta"),
    ("contrato", "Contrato"),
    ("pagamento", "Pagamento"),
    ("cancelamento", "Cancelamento"),
    ("mensagem", "Mensagem"),
    ("avaliacao", "Avaliação"),
    ("moderacao", "Moderação"),
    ("lembrete", "Lembrete"),
    ("suporte", "Suporte"),
]

MOTIVOS_DENUNCIA = [
    ("ofensivo", "Conteúdo ofensivo ou discriminatório"),
    ("falso", "Informação falsa ou avaliação de quem não contratou"),
    ("spam", "Propaganda ou spam"),
    ("golpe", "Tentativa de golpe ou pagamento por fora"),
    ("outro", "Outro motivo"),
]

STATUS_DENUNCIA = [
    ("aberta", "Aberta"),
    ("procedente", "Procedente"),
    ("improcedente", "Improcedente"),
]

TIPOS_PORTFOLIO = [
    ("foto", "Foto"),
    ("video", "Vídeo"),
    ("audio", "Áudio"),
]


# ---------------------------------------------------------------
# Usuários
# O login (usuário e senha) usa o User do próprio Django.
# O Perfil guarda o resto dos dados e o papel de cada conta.
# ---------------------------------------------------------------
class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=30, blank=True)
    cidade = models.CharField(max_length=80, blank=True)
    estado = models.CharField(max_length=2, choices=ESTADOS, blank=True)
    ano_nascimento = models.PositiveSmallIntegerField(null=True, blank=True)
    mes_nascimento = models.PositiveSmallIntegerField(choices=MESES, null=True, blank=True)
    papel = models.CharField(max_length=10, choices=PAPEIS, default="cliente")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "perfis"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.nome + " (" + self.user.username + ")"

    @property
    def idade(self):
        """Calculada na hora, a partir do mês e do ano de nascimento (None se a conta não informou)."""
        if self.ano_nascimento is None or self.mes_nascimento is None:
            return None
        return calcular_idade(self.ano_nascimento, self.mes_nascimento, timezone.localdate())


class Categoria(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    descricao = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class ArtistaQuerySet(models.QuerySet):
    def com_nota(self):
        """Acrescenta nota_media e total_avaliacoes (sem contar avaliações ocultas pela moderação)."""
        visiveis = Q(avaliacoes__oculta=False)
        return self.select_related("categoria").annotate(
            nota_media=Round(Avg("avaliacoes__nota", filter=visiveis), 1),
            total_avaliacoes=Count("avaliacoes", filter=visiveis),
        )


class Artista(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="artista")
    nome_artistico = models.CharField(max_length=120)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="artistas")
    estilo = models.CharField(max_length=80, blank=True)
    cidade = models.CharField(max_length=80)
    preco_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(blank=True)
    foto_url = models.CharField(max_length=500, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = ArtistaQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["categoria", "cidade"])]
        constraints = [models.CheckConstraint(condition=Q(preco_minimo__gte=0), name="artista_preco_positivo")]

    def __str__(self):
        return self.nome_artistico


class Evento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=20, choices=TIPOS_EVENTO)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    data_evento = models.DateField(null=True, blank=True)
    localizacao = models.CharField(max_length=200, blank=True)
    orcamento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_tipo_display() + " de " + self.cliente.username


class PedidoOrcamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="pedidos")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    data_evento = models.DateField()
    horario_inicio = models.TimeField()
    duracao_horas = models.DecimalField(max_digits=4, decimal_places=1)
    estimativa_convidados = models.PositiveIntegerField()
    local = models.CharField(max_length=200)
    observacoes = models.TextField(max_length=600, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_ORCAMENTO, default="aberto")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pedido de orçamento"
        verbose_name_plural = "pedidos de orçamento"

    def __str__(self):
        return "Pedido de " + str(self.categoria) + " para " + self.data_evento.strftime("%d/%m/%Y")


class Proposta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pedido = models.ForeignKey(PedidoOrcamento, on_delete=models.CASCADE, related_name="propostas")
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, related_name="propostas")
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    mensagem = models.TextField(blank=True)
    data_sugerida = models.DateField(null=True, blank=True)       # preenchida quando é contraproposta de data
    horario_sugerido = models.TimeField(null=True, blank=True)    # preenchido quando é contraproposta de horário
    status = models.CharField(max_length=20, choices=STATUS_PROPOSTA, default="enviada")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pedido", "artista"], name="uma_resposta_por_artista"),
            models.CheckConstraint(condition=Q(status="declinada") | Q(valor__isnull=False), name="proposta_com_valor"),
        ]

    def __str__(self):
        return "Proposta de " + str(self.artista)


class Contrato(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="contratos")
    proposta = models.OneToOneField(Proposta, on_delete=models.PROTECT, null=True, blank=True, related_name="contrato")
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contratos")
    artista = models.ForeignKey(Artista, on_delete=models.PROTECT, related_name="contratos")
    descricao = models.CharField(max_length=200, blank=True)
    data_evento = models.DateField()
    local = models.CharField(max_length=200)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=25, choices=STATUS_CONTRATO, default="aguardando_pagamento")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.artista) + " em " + self.data_evento.strftime("%d/%m/%Y")


class Pagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="pagamentos")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=20, blank=True)
    cupom = models.ForeignKey("Cupom", on_delete=models.PROTECT, null=True, blank=True, related_name="pagamentos")
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)   # pago pela plataforma
    status = models.CharField(max_length=20, choices=STATUS_PAGAMENTO, default="pendente")
    pago_em = models.DateTimeField(null=True, blank=True)
    liberado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
        constraints = [models.CheckConstraint(condition=Q(valor__gt=0), name="pagamento_valor_positivo")]


class Avaliacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.OneToOneField(Contrato, on_delete=models.CASCADE, related_name="avaliacao")
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, related_name="avaliacoes")
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="avaliacoes")
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, null=True)
    oculta = models.BooleanField(default=False)   # escondida pela moderação
    resposta = models.TextField(max_length=500, blank=True)   # resposta pública do artista
    respondida_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "avaliação"
        verbose_name_plural = "avaliações"
        constraints = [models.CheckConstraint(condition=Q(nota__gte=1, nota__lte=5), name="nota_de_1_a_5")]


class Mensagem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, null=True, blank=True, related_name="mensagens")
    remetente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensagens_enviadas")
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mensagens_recebidas")
    conteudo = models.TextField()
    lida = models.BooleanField(default=False)
    enviada_em = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "mensagens"
        ordering = ["enviada_em"]
        indexes = [models.Index(fields=["destinatario", "lida"])]


class ChamadoSuporte(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chamados")
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_SUPORTE, default="duvida")
    contrato = models.ForeignKey("Contrato", on_delete=models.SET_NULL, null=True, blank=True, related_name="chamados")
    assunto = models.CharField(max_length=120)
    descricao = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_SUPORTE, default="aberto")
    prazo_resposta = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "chamado de suporte"
        verbose_name_plural = "chamados de suporte"
        ordering = ["-criado_em"]

    def __str__(self):
        return self.assunto


class MensagemChamado(models.Model):
    """Conversa dentro de um chamado de suporte (usuário e equipe)."""
    chamado = models.ForeignKey(ChamadoSuporte, on_delete=models.CASCADE, related_name="mensagens")
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    da_equipe = models.BooleanField(default=False)
    texto = models.TextField(max_length=1000)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]


class Disponibilidade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, related_name="agenda")
    data = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_AGENDA, default="ocupado")
    observacao = models.CharField(max_length=120, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "disponibilidade"
        ordering = ["data"]
        constraints = [models.UniqueConstraint(fields=["artista", "data"], name="uma_marcacao_por_dia")]


class TokenSenha(models.Model):
    """Guarda só o hash do token; o token em si vai apenas no link enviado por e-mail."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tokens_senha")
    token_hash = models.CharField(max_length=64, unique=True)
    expira_em = models.DateTimeField()
    usado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)


# ---------------------------------------------------------------
# Sprint 7
# ---------------------------------------------------------------
class Favorito(models.Model):
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favoritos")
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, related_name="favoritado_por")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [models.UniqueConstraint(fields=["cliente", "artista"], name="favorito_unico")]


class Notificacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notificacoes")
    tipo = models.CharField(max_length=20, choices=TIPOS_NOTIFICACAO)
    texto = models.CharField(max_length=200)
    link = models.CharField(max_length=300, blank=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "notificação"
        verbose_name_plural = "notificações"
        ordering = ["-criada_em"]
        indexes = [models.Index(fields=["user", "lida", "-criada_em"])]


class Cancelamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.OneToOneField(Contrato, on_delete=models.CASCADE, related_name="cancelamento")
    cancelado_por = models.CharField(max_length=10, choices=[("cliente", "cliente"), ("artista", "artista")])
    motivo = models.CharField(max_length=300)
    dias_antecedencia = models.IntegerField()
    percentual_reembolso = models.IntegerField()
    valor_reembolso = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_artista = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    criado_em = models.DateTimeField(auto_now_add=True)


class Denuncia(models.Model):
    """Denúncia de um perfil de artista OU de uma avaliação (nunca os dois)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    denunciante = models.ForeignKey(User, on_delete=models.CASCADE, related_name="denuncias")
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, null=True, blank=True, related_name="denuncias")
    avaliacao = models.ForeignKey(Avaliacao, on_delete=models.CASCADE, null=True, blank=True, related_name="denuncias")
    motivo = models.CharField(max_length=20, choices=MOTIVOS_DENUNCIA)
    detalhes = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_DENUNCIA, default="aberta")
    decisao = models.CharField(max_length=300, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    resolvida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "denúncia"
        ordering = ["criada_em"]
        constraints = [
            models.CheckConstraint(
                condition=Q(artista__isnull=True, avaliacao__isnull=False) | Q(artista__isnull=False, avaliacao__isnull=True),
                name="denuncia_de_um_conteudo",
            ),
            # a mesma pessoa não denuncia o mesmo conteúdo duas vezes enquanto a denúncia está aberta
            models.UniqueConstraint(fields=["denunciante", "artista"], condition=Q(status="aberta", artista__isnull=False),
                                    name="denuncia_unica_artista"),
            models.UniqueConstraint(fields=["denunciante", "avaliacao"], condition=Q(status="aberta", avaliacao__isnull=False),
                                    name="denuncia_unica_avaliacao"),
        ]


class Portfolio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artista = models.ForeignKey(Artista, on_delete=models.CASCADE, related_name="portfolio")
    tipo = models.CharField(max_length=10, choices=TIPOS_PORTFOLIO)
    titulo = models.CharField(max_length=80)
    url = models.CharField(max_length=500)   # link https:// ou imagem da própria plataforma (/static/...)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "portfólio"
        ordering = ["criado_em"]


# ---------------------------------------------------------------
# Sprint 8
# ---------------------------------------------------------------
class Cupom(models.Model):
    codigo = models.CharField(max_length=20, unique=True)   # sempre em maiúsculas
    descricao = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPOS_CUPOM)
    valor = models.DecimalField(max_digits=10, decimal_places=2)        # 10 = 10% ou R$ 10
    valor_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    desconto_maximo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    validade = models.DateField(null=True, blank=True)
    limite_usos = models.PositiveIntegerField(null=True, blank=True)    # vazio = sem limite
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "cupons"
        constraints = [
            models.CheckConstraint(condition=Q(valor__gt=0), name="cupom_valor_positivo"),
            models.CheckConstraint(condition=~Q(tipo="percentual") | Q(valor__lte=100), name="cupom_percentual_ate_100"),
        ]

    def __str__(self):
        return self.codigo


class LembreteEnviado(models.Model):
    """Evita mandar o mesmo lembrete duas vezes para a mesma pessoa."""
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name="lembretes")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    antecedencia = models.CharField(max_length=10, choices=[("7dias", "7 dias antes"), ("1dia", "1 dia antes")])
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["contrato", "user", "antecedencia"], name="lembrete_unico")]
