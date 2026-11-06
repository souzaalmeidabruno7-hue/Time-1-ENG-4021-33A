"""Testes automatizados do ArtConnect.

Rodar:  python manage.py test
O Django cria um banco de teste separado e coloca os dados de exemplo nele.
"""
import re
from io import StringIO
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from ArtConnect.dados_exemplo import SENHA_PADRAO, popular
from ArtConnect.match import calcular_compatibilidade
from ArtConnect.models import (Artista, Avaliacao, Cancelamento, Categoria, ChamadoSuporte, Contrato, Cupom, Denuncia, Disponibilidade,
                               Favorito, Mensagem, Notificacao, Pagamento, PedidoOrcamento, Perfil, Portfolio,
                               Proposta, TokenSenha, calcular_idade)
from ArtConnect.politicas import dividir_valor, link_embed, percentual_reembolso
from ArtConnect.views import hash_token


class ArtistaFalso:
    """Só os campos que o cálculo de compatibilidade usa."""

    def __init__(self, preco_minimo, cidade, nota_media):
        self.preco_minimo = preco_minimo
        self.cidade = cidade
        self.nota_media = nota_media


# senha com hash rápido: os testes rodam bem mais depressa
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BaseArtConnect(TestCase):

    @classmethod
    def setUpTestData(cls):
        popular(mostrar=False)

    # ---------- funções de apoio ----------
    def entrar(self, username):
        self.client.logout()
        return self.client.post("/login", {"username": username, "password": SENHA_PADRAO})

    def texto(self, resposta):
        return resposta.content.decode("utf-8")

    def seguir(self, resposta):
        """Abre a página para onde o redirect leva (equivale ao follow_redirects)."""
        return self.client.get(resposta["Location"])

    def artista(self, nome):
        return Artista.objects.get(nome_artistico=nome)

    def contrato(self, username, nome_artistico):
        return Contrato.objects.get(cliente__username=username, artista__nome_artistico=nome_artistico)

    def proposta(self, nome_artistico):
        return Proposta.objects.get(artista__nome_artistico=nome_artistico)

    def pedido(self, username):
        return PedidoOrcamento.objects.get(evento__cliente__username=username)

    def categoria(self, slug):
        return str(Categoria.objects.get(slug=slug).id)

    def notificacoes_de(self, username):
        return list(Notificacao.objects.filter(user__username=username).order_by("-criada_em"))

    def aceitar_selva(self):
        """luiz aceita a proposta da Selva Ritmo: cria um contrato futuro aguardando pagamento."""
        self.entrar("luiz")
        self.client.post("/propostas/" + str(self.proposta("Selva Ritmo").id) + "/aceitar")
        return Contrato.objects.get(proposta__artista__nome_artistico="Selva Ritmo")


# ---------------------------------------------------------------
# Rotas principais
# ---------------------------------------------------------------
class TestRotas(BaseArtConnect):

    def test_home_lista_artistas(self):
        resposta = self.client.get("/")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Selva Ritmo", self.texto(resposta))

    def test_perfil_do_artista(self):
        resposta = self.client.get("/artistas/" + str(self.artista("Coletivo Maré").id))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Coletivo Maré", self.texto(resposta))

    def test_artista_com_id_invalido_nao_da_erro_500(self):
        resposta = self.client.get("/artistas/nao-e-um-id", follow=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Artista não encontrado", self.texto(resposta))

    def test_painel_exige_login(self):
        resposta = self.client.get("/painel")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/login", resposta["Location"])
        self.assertIn("Entre na sua conta para continuar", self.texto(self.seguir(resposta)))

    def test_login_com_senha_errada(self):
        resposta = self.client.post("/login", {"username": "luiz", "password": "errada"})
        self.assertEqual(resposta.status_code, 401)

    def test_login_leva_cada_papel_ao_seu_painel(self):
        self.assertTrue(self.entrar("luiz")["Location"].endswith("/painel"))
        self.assertTrue(self.entrar("selvaritmo")["Location"].endswith("/artista/painel"))
        self.assertTrue(self.entrar("admin")["Location"].endswith("/admin"))

    def test_login_volta_para_a_pagina_pedida(self):
        resposta = self.client.post("/login?next=/orcamento", {"username": "luiz", "password": SENHA_PADRAO})
        self.assertEqual(resposta["Location"], "/orcamento")

    def test_cadastro_de_cliente(self):
        dados = {"tipo": "contratante", "username": "maria", "nome": "Maria Lima", "email": "maria@x.com",
                 "estado": "RJ", "mes_nascimento": "5", "ano_nascimento": "1999", "senha": "12345678", "confirmar": "12345678", "termos": "on"}
        resposta = self.client.post("/cadastro", dados)
        self.assertEqual(resposta.status_code, 302)
        perfil = Perfil.objects.get(user__username="maria")
        self.assertEqual(perfil.papel, "cliente")
        self.assertEqual(perfil.estado, "RJ")
        self.assertEqual(perfil.get_estado_display(), "Rio de Janeiro")
        self.assertEqual(perfil.mes_nascimento, 5)
        self.assertEqual(perfil.ano_nascimento, 1999)
        self.assertEqual(perfil.idade, calcular_idade(1999, 5, date.today()))

    def test_cadastro_mostra_os_27_estados(self):
        pagina = self.client.get("/cadastro").content.decode()
        self.assertEqual(pagina.count('<option value="') - pagina.count('<option value=""'),
                         27 + 12 + 103 + Categoria.objects.count())
        self.assertIn("Rio de Janeiro (RJ)", pagina)
        self.assertIn("Tocantins (TO)", pagina)
        self.assertIn(">Dezembro</option>", pagina)
        # o ano mais recente da lista é o de quem faz 18 anos este ano
        self.assertIn('<option value="' + str(date.today().year - 18) + '"', pagina)
        self.assertNotIn('<option value="' + str(date.today().year - 17) + '"', pagina)

    def test_idade_pelo_mes_e_ano(self):
        hoje = date(2026, 11, 6)
        self.assertEqual(calcular_idade(2008, 10, hoje), 18)   # já fez 18 em outubro
        self.assertEqual(calcular_idade(2008, 11, hoje), 18)   # mês do aniversário conta como feito
        self.assertEqual(calcular_idade(2008, 12, hoje), 17)   # só faz 18 em dezembro

    def test_cadastro_recusa_estado_fora_da_lista_e_idade_invalida(self):
        base = {"tipo": "contratante", "username": "ana", "nome": "Ana Lima", "email": "ana@x.com",
                "senha": "12345678", "confirmar": "12345678", "termos": "on"}
        ano_17 = str(date.today().year - 17)
        casos = [
            ({"estado": "Rio", "mes_nascimento": "5", "ano_nascimento": "1990"}, "Escolha o seu estado na lista."),
            ({"estado": "", "mes_nascimento": "5", "ano_nascimento": "1990"}, "Escolha o seu estado na lista."),
            ({"estado": "SP", "mes_nascimento": "", "ano_nascimento": "1990"}, "Escolha o mês em que você nasceu."),
            ({"estado": "SP", "mes_nascimento": "13", "ano_nascimento": "1990"}, "Escolha o mês em que você nasceu."),
            ({"estado": "SP", "mes_nascimento": "5", "ano_nascimento": ""}, "Escolha o ano em que você nasceu."),
            ({"estado": "SP", "mes_nascimento": "1", "ano_nascimento": ano_17}, "ao menos 18 anos"),
            ({"estado": "SP", "mes_nascimento": "5", "ano_nascimento": "1800"}, "Escolha um ano de nascimento válido."),
        ]
        for extra, mensagem in casos:
            dados = dict(base)
            dados.update(extra)
            resposta = self.client.post("/cadastro", dados)
            self.assertEqual(resposta.status_code, 400)
            self.assertIn(mensagem, self.texto(resposta))
        self.assertFalse(User.objects.filter(username="ana").exists())

    def test_cadastro_de_artista_com_preco_invalido_nao_cria_conta(self):
        dados = {"tipo": "artista", "username": "novo_dj", "nome": "Novo DJ", "email": "dj@x.com",
                 "estado": "RJ", "mes_nascimento": "3", "ano_nascimento": "1996", "cidade": "Rio de Janeiro", "categoria": self.categoria("djs"), "preco": "abc",
                 "senha": "12345678", "confirmar": "12345678", "termos": "on"}
        resposta = self.client.post("/cadastro", dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(User.objects.filter(username="novo_dj").exists())

        # corrigindo o preço, o mesmo usuário consegue se cadastrar
        dados["preco"] = "1500"
        resposta = self.client.post("/cadastro", dados)
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(float(Artista.objects.get(user__username="novo_dj").preco_minimo), 1500)

    def test_artista_precisa_informar_a_cidade(self):
        dados = {"tipo": "artista", "username": "dj_sem_cidade", "nome": "DJ Sem Cidade", "email": "sc@x.com",
                 "estado": "RJ", "mes_nascimento": "3", "ano_nascimento": "1996", "cidade": "", "categoria": self.categoria("djs"), "preco": "800",
                 "senha": "12345678", "confirmar": "12345678", "termos": "on"}
        resposta = self.client.post("/cadastro", dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("Informe a cidade onde você se apresenta.", self.texto(resposta))

    def test_cadastro_duplicado(self):
        dados = {"tipo": "contratante", "username": "luiz", "nome": "Outro Luiz", "email": "outro@x.com",
                 "estado": "RJ", "mes_nascimento": "7", "ano_nascimento": "1986", "senha": "12345678", "confirmar": "12345678", "termos": "on"}
        resposta = self.client.post("/cadastro", dados)
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("já está cadastrado", self.texto(resposta))

    def test_pedido_de_orcamento(self):
        self.entrar("helena")
        data = (date.today() + timedelta(days=30)).isoformat()
        dados = {"tipo_evento": "aniversario", "categoria": self.categoria("magicos"), "data": data, "horario": "18:00",
                 "duracao": "2", "convidados": "40", "local": "Rua das Flores, 10"}
        resposta = self.client.post("/orcamento", dados)
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(PedidoOrcamento.objects.filter(evento__cliente__username="helena").count(), 2)

    def test_pedido_de_orcamento_com_erros(self):
        self.entrar("helena")
        resposta = self.client.post("/orcamento", {"data": "2020-01-01", "local": "x"})
        self.assertEqual(resposta.status_code, 400)
        self.assertIn("A data não pode estar no passado", self.texto(resposta))

    def test_listagem_de_usuarios_so_para_admin(self):
        self.entrar("luiz")
        self.assertEqual(self.client.get("/usuarios").status_code, 302)
        self.entrar("admin")
        resposta = self.client.get("/usuarios?busca=gullo")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Luiz Gullo", self.texto(resposta))
        self.assertNotIn("Helena Prado", self.texto(resposta))

    def test_editar_perfil(self):
        self.entrar("luiz")
        self.client.post("/perfil/editar", {"nome": "Luiz R. Gullo", "email": "luiz@exemplo.com",
                                            "telefone": "", "estado": "SP", "mes_nascimento": "3", "ano_nascimento": "2005", "nova_senha": ""})
        perfil = Perfil.objects.get(user__username="luiz")
        self.assertEqual(perfil.nome, "Luiz R. Gullo")
        self.assertEqual(perfil.estado, "SP")
        self.assertEqual(perfil.ano_nascimento, 2005)
        self.assertEqual(perfil.mes_nascimento, 3)

    def test_exclusao_bloqueada_com_pagamento_retido(self):
        self.entrar("luiz")
        dados = {"password": SENHA_PADRAO, "confirm_text": "EXCLUIR", "confirm_check": "on"}
        resposta = self.client.post("/conta/excluir", dados)
        self.assertIn("pagamento retido", self.texto(resposta))
        self.assertTrue(User.objects.filter(username="luiz").exists())

    def test_exclusao_de_conta(self):
        self.entrar("rafael")
        dados = {"password": SENHA_PADRAO, "confirm_text": "EXCLUIR", "confirm_check": "on"}
        self.client.post("/conta/excluir", dados)
        self.assertFalse(User.objects.filter(username="rafael").exists())

    def test_pagina_inexistente(self):
        self.assertEqual(self.client.get("/nao-existe").status_code, 404)


# ---------------------------------------------------------------
# Match de compatibilidade
# ---------------------------------------------------------------
class TestMatch(BaseArtConnect):

    def test_regras_de_pontuacao(self):
        artista = ArtistaFalso(1800, "Rio de Janeiro", 4.0)
        # todos os critérios: 35 (preço) + 25 (cidade) + 25 (livre) + 12 (nota 4) = 97 de 100
        self.assertEqual(calcular_compatibilidade(artista, "Rio de Janeiro", 2000, True, False), 97)
        # 20% acima do orçamento vale 15; ocupado na data vale 0: 15 + 25 + 0 + 12 = 52
        self.assertEqual(calcular_compatibilidade(artista, "rio de janeiro", 1600, True, True), 52)
        # sem avaliação conta metade da nota (7,5 de 15): só nota informada = 50%
        novo = ArtistaFalso(500, "Recife", None)
        self.assertEqual(calcular_compatibilidade(novo, "", None, False, False), 50)

    def test_busca_ordena_por_compatibilidade(self):
        pagina = self.texto(self.client.get("/?cidade=Rio+de+Janeiro&orcamento=2000"))
        self.assertIn("Mais compatíveis com seu evento", pagina)
        numeros = []
        for valor in re.findall(r"(\d+)% compatível", pagina):
            numeros.append(int(valor))
        self.assertEqual(len(numeros), 11)
        self.assertEqual(numeros, sorted(numeros, reverse=True))
        # o primeiro resultado é do Rio e cabe no orçamento
        self.assertLess(pagina.index("Coletivo Maré"), pagina.index("Chef Raiz"))

    def test_busca_marca_artista_ocupado_na_data(self):
        pagina = self.texto(self.client.get("/?categoria=" + self.categoria("djs") + "&data=2026-12-05"))
        self.assertIn("ocupado na data", pagina)
        self.assertLess(pagina.index("Neon Sombra"), pagina.index("Selva Ritmo"))

    def test_busca_com_orcamento_invalido(self):
        resposta = self.client.get("/?orcamento=muito")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("só com números", self.texto(resposta))


# ---------------------------------------------------------------
# Painel do artista: agenda, propostas e contrapropostas
# ---------------------------------------------------------------
class TestPainelArtista(BaseArtConnect):

    def test_artista_marca_e_remove_data(self):
        self.entrar("coletivomare")
        data = date.today() + timedelta(days=40)
        self.client.post("/artista/agenda", {"data": data.isoformat(), "status": "ocupado", "observacao": "Turnê"})
        marcacao = Disponibilidade.objects.get(artista=self.artista("Coletivo Maré"), data=data)
        self.assertEqual(marcacao.status, "ocupado")

        self.client.post("/artista/agenda", {"data": data.isoformat(), "acao": "remover"})
        self.assertFalse(Disponibilidade.objects.filter(artista=self.artista("Coletivo Maré"), data=data).exists())

    def test_agenda_nao_aceita_data_passada(self):
        self.entrar("coletivomare")
        resposta = self.client.post("/artista/agenda", {"data": "2020-01-01", "status": "ocupado"}, follow=True)
        self.assertIn("a partir de hoje", self.texto(resposta))

    def test_cliente_nao_acessa_painel_do_artista(self):
        self.entrar("luiz")
        self.assertEqual(self.client.get("/artista/painel").status_code, 302)

    def test_painel_do_artista_mostra_pedidos_da_categoria(self):
        self.entrar("selvaritmo")
        pagina = self.texto(self.client.get("/artista/painel"))
        self.assertIn("Rooftop Centro", pagina)              # pedido de DJ do rafael
        self.assertNotIn("Salão Vila Madalena", pagina)      # pedido de cantor, outra categoria
        self.assertNotIn("Casa de Festas Lagoa", pagina)     # pedido que ele já respondeu
        self.assertIn("agenda está marcada como ocupada", pagina)

    def test_artista_envia_proposta(self):
        self.entrar("neonsombra")
        resposta = self.client.post("/artista/pedidos/" + str(self.pedido("rafael").id) + "/responder",
                                    {"acao": "proposta", "valor": "3300", "mensagem": "Set de 5h"})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(self.pedido("rafael").status, "com_propostas")

    def test_proposta_bloqueada_quando_agenda_ocupada_e_contraproposta_liberada(self):
        self.entrar("selvaritmo")
        url = "/artista/pedidos/" + str(self.pedido("rafael").id) + "/responder"
        resposta = self.client.post(url, {"acao": "proposta", "valor": "2500"}, follow=True)
        self.assertIn("Envie uma contraproposta", self.texto(resposta))

        self.client.post(url, {"acao": "contraproposta", "valor": "2500", "data_sugerida": "2026-12-06"})
        proposta = Proposta.objects.get(pedido=self.pedido("rafael"))
        self.assertEqual(proposta.data_sugerida, date(2026, 12, 6))

    def test_artista_recusa_pedido(self):
        self.entrar("neonsombra")
        self.client.post("/artista/pedidos/" + str(self.pedido("rafael").id) + "/responder", {"acao": "recusar"})
        self.assertEqual(Proposta.objects.get(pedido=self.pedido("rafael")).status, "declinada")
        self.assertNotIn("Rooftop Centro", self.texto(self.client.get("/artista/painel")))

    def test_artista_nao_responde_duas_vezes(self):
        self.entrar("neonsombra")
        url = "/artista/pedidos/" + str(self.pedido("rafael").id) + "/responder"
        self.client.post(url, {"acao": "recusar"})
        resposta = self.client.post(url, {"acao": "proposta", "valor": "100"}, follow=True)
        self.assertIn("já respondeu", self.texto(resposta))

    def test_cliente_aceita_proposta_e_gera_contrato(self):
        self.entrar("luiz")
        resposta = self.client.post("/propostas/" + str(self.proposta("Selva Ritmo").id) + "/aceitar")
        self.assertEqual(resposta.status_code, 302)

        contrato = Contrato.objects.get(proposta=self.proposta("Selva Ritmo"))
        self.assertEqual(float(contrato.valor_total), 2800)
        self.assertEqual(contrato.pagamentos.get().status, "pendente")
        self.assertEqual(self.proposta("Neon Sombra").status, "recusada")
        self.assertEqual(self.pedido("luiz").status, "fechado")
        agenda = Disponibilidade.objects.get(artista=self.artista("Selva Ritmo"), data=contrato.data_evento)
        self.assertEqual(agenda.status, "ocupado")

    def test_aceitar_contraproposta_usa_a_data_sugerida(self):
        self.entrar("luiz")
        self.client.post("/propostas/" + str(self.proposta("Neon Sombra").id) + "/aceitar")
        contrato = Contrato.objects.get(proposta=self.proposta("Neon Sombra"))
        self.assertEqual(contrato.data_evento, date(2026, 12, 13))

    def test_cliente_nao_aceita_proposta_de_outra_pessoa(self):
        self.entrar("helena")
        resposta = self.client.post("/propostas/" + str(self.proposta("Selva Ritmo").id) + "/aceitar", follow=True)
        self.assertIn("Proposta não encontrada", self.texto(resposta))
        self.assertEqual(self.proposta("Selva Ritmo").status, "enviada")

    def test_cliente_recusa_proposta(self):
        self.entrar("luiz")
        self.client.post("/propostas/" + str(self.proposta("Selva Ritmo").id) + "/recusar")
        self.assertEqual(self.proposta("Selva Ritmo").status, "recusada")
        self.assertEqual(self.notificacoes_de("selvaritmo")[0].texto, "Luiz Gullo recusou sua proposta.")


# ---------------------------------------------------------------
# Confirmação do evento e avaliação
# ---------------------------------------------------------------
class TestAvaliacao(BaseArtConnect):

    def test_confirmar_evento_libera_pagamento(self):
        self.entrar("luiz")
        contrato = self.contrato("luiz", "Selva Ritmo")
        self.client.post("/contratos/" + str(contrato.id) + "/confirmar")
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, "concluido")
        self.assertEqual(contrato.pagamentos.get().status, "liberado")

    def test_nao_confirma_evento_futuro(self):
        self.entrar("luiz")
        contrato = self.contrato("luiz", "Neon Sombra")
        resposta = self.client.post("/contratos/" + str(contrato.id) + "/confirmar", follow=True)
        self.assertIn("depois da data do evento", self.texto(resposta))

    def test_avaliar_contrato_concluido_atualiza_nota(self):
        self.entrar("luiz")
        contrato = self.contrato("luiz", "Estúdio Lume")
        resposta = self.client.post("/contratos/" + str(contrato.id) + "/avaliar",
                                    {"nota": "4", "comentario": "Fotos lindas, entregaram em uma semana."})
        self.assertEqual(resposta.status_code, 302)
        artista = Artista.objects.com_nota().get(nome_artistico="Estúdio Lume")
        self.assertEqual(float(artista.nota_media), 4.0)
        self.assertEqual(artista.total_avaliacoes, 1)

    def test_nao_avalia_duas_vezes(self):
        self.entrar("luiz")
        contrato = self.contrato("luiz", "Estúdio Lume")
        self.client.post("/contratos/" + str(contrato.id) + "/avaliar", {"nota": "5"})
        resposta = self.client.post("/contratos/" + str(contrato.id) + "/avaliar", {"nota": "1"}, follow=True)
        self.assertIn("já avaliou", self.texto(resposta))

    def test_nao_avalia_evento_nao_concluido(self):
        self.entrar("luiz")
        contrato = self.contrato("luiz", "Neon Sombra")
        resposta = self.client.get("/contratos/" + str(contrato.id) + "/avaliar", follow=True)
        self.assertIn("depois que o evento for concluído", self.texto(resposta))

    def test_nota_fora_do_intervalo(self):
        self.entrar("luiz")
        contrato = self.contrato("luiz", "Estúdio Lume")
        resposta = self.client.post("/contratos/" + str(contrato.id) + "/avaliar", {"nota": "9"})
        self.assertEqual(resposta.status_code, 400)


# ---------------------------------------------------------------
# Recuperação de senha
# ---------------------------------------------------------------
class TestSenha(BaseArtConnect):

    def test_recuperacao_de_senha_completa(self):
        self.client.post("/senha/esqueci", {"email": "luiz@exemplo.com"})
        self.assertEqual(len(mail.outbox), 1)
        caminho = re.search(r"/senha/redefinir/\S+", mail.outbox[0].body).group(0)

        self.assertEqual(self.client.get(caminho).status_code, 200)
        self.client.post(caminho, {"senha": "novasenha99", "confirmar": "novasenha99"})
        resposta = self.client.post("/login", {"username": "luiz", "password": "novasenha99"})
        self.assertEqual(resposta.status_code, 302)

        # o link não pode ser usado de novo
        resposta = self.client.get(caminho, follow=True)
        self.assertIn("inválido ou expirado", self.texto(resposta))

    def test_email_desconhecido_recebe_a_mesma_mensagem(self):
        resposta = self.client.post("/senha/esqueci", {"email": "ninguem@x.com"}, follow=True)
        self.assertIn("Se esse e-mail estiver cadastrado", self.texto(resposta))
        self.assertEqual(len(mail.outbox), 0)

    def test_token_expirado_nao_funciona(self):
        TokenSenha.objects.create(user=User.objects.get(username="luiz"), token_hash=hash_token("token-velho"),
                                  expira_em=timezone.now() - timedelta(minutes=1))
        resposta = self.client.get("/senha/redefinir/token-velho", follow=True)
        self.assertIn("inválido ou expirado", self.texto(resposta))


# ---------------------------------------------------------------
# Dashboard administrativo
# ---------------------------------------------------------------
class TestAdmin(BaseArtConnect):

    def test_dashboard_admin(self):
        self.entrar("admin")
        resposta = self.client.get("/admin")
        pagina = self.texto(resposta)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("Dashboard da plataforma", pagina)
        self.assertIn("Demanda por categoria", pagina)
        self.assertIn("Risada Tardia", pagina)

    def test_dashboard_bloqueado_para_cliente(self):
        self.entrar("luiz")
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_admin_do_django(self):
        self.entrar("admin")
        self.assertEqual(self.client.get("/django-admin/").status_code, 200)


# ---------------------------------------------------------------
# Regras de negócio (politicas.py)
# ---------------------------------------------------------------
class TestPoliticas(TestCase):

    def test_percentual_de_reembolso_segue_a_politica(self):
        self.assertEqual(percentual_reembolso("cliente", 45, 100), 100)
        self.assertEqual(percentual_reembolso("cliente", 30, 100), 100)
        self.assertEqual(percentual_reembolso("cliente", 20, 100), 70)
        self.assertEqual(percentual_reembolso("cliente", 10, 100), 50)
        self.assertEqual(percentual_reembolso("cliente", 3, 100), 0)
        # arrependimento em 24h só vale com o evento a mais de 7 dias
        self.assertEqual(percentual_reembolso("cliente", 10, 5), 100)
        self.assertEqual(percentual_reembolso("cliente", 5, 5), 0)
        # cancelamento pelo artista devolve tudo
        self.assertEqual(percentual_reembolso("artista", 1, 500), 100)

    def test_divisao_do_valor(self):
        self.assertEqual(dividir_valor(3080, 70), (2156.0, 924.0))
        self.assertEqual(dividir_valor(1000, 0), (0, 1000.0))

    def test_link_de_video_vira_embed(self):
        self.assertEqual(link_embed("https://www.youtube.com/watch?v=abc123XYZ_-"),
                         "https://www.youtube-nocookie.com/embed/abc123XYZ_-")
        self.assertEqual(link_embed("https://youtu.be/abc123"), "https://www.youtube-nocookie.com/embed/abc123")
        self.assertEqual(link_embed("https://vimeo.com/76979871"), "https://player.vimeo.com/video/76979871")
        self.assertEqual(link_embed("https://exemplo.com/video.mp4"), "")
        self.assertEqual(link_embed("https://www.youtube.com/watch?v=<script>"), "")


# ---------------------------------------------------------------
# Pagamento simulado
# ---------------------------------------------------------------
class TestPagamento(BaseArtConnect):

    def test_pagamento_retem_o_valor_e_avisa_o_artista(self):
        contrato = self.aceitar_selva()
        self.assertEqual(self.client.get("/contratos/" + str(contrato.id) + "/pagar").status_code, 200)

        resposta = self.client.post("/contratos/" + str(contrato.id) + "/pagar", {"metodo": "pix", "ciente": "on"},
                                    follow=True)
        self.assertIn("Pagamento confirmado", self.texto(resposta))
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, "valor_retido")
        pagamento = contrato.pagamentos.get()
        self.assertEqual(pagamento.status, "retido")
        self.assertEqual(pagamento.metodo, "pix")
        self.assertIsNotNone(pagamento.pago_em)
        self.assertIn("Pagamento de R$ 2.800 confirmado", self.notificacoes_de("selvaritmo")[0].texto)

    def test_pagamento_exige_metodo_e_ciencia(self):
        contrato = self.aceitar_selva()
        url = "/contratos/" + str(contrato.id) + "/pagar"
        self.assertEqual(self.client.post(url, {"metodo": "cartao", "ciente": "on"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"metodo": "pix"}).status_code, 400)
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, "aguardando_pagamento")

    def test_nao_paga_contrato_ja_pago_nem_de_outro_cliente(self):
        url = "/contratos/" + str(self.contrato("luiz", "Neon Sombra").id) + "/pagar"
        self.entrar("helena")
        self.assertIn("Contrato não encontrado", self.texto(self.client.get(url, follow=True)))
        self.entrar("luiz")
        self.assertIn("não está aguardando pagamento", self.texto(self.client.get(url, follow=True)))


# ---------------------------------------------------------------
# Cancelamento com reembolso
# ---------------------------------------------------------------
class TestCancelamento(BaseArtConnect):

    def test_cancelamento_pelo_cliente_com_reembolso_parcial(self):
        contrato = self.contrato("luiz", "Neon Sombra")
        # evento daqui a 20 dias, contrato fechado há 10 dias -> faixa de 70%
        Contrato.objects.filter(id=contrato.id).update(data_evento=date.today() + timedelta(days=20),
                                                       criado_em=timezone.now() - timedelta(days=10))
        self.entrar("luiz")
        url = "/contratos/" + str(contrato.id) + "/cancelar"
        self.assertIn("70%", self.texto(self.client.get(url)))

        resposta = self.client.post(url, {"motivo": "Evento adiado pela empresa", "confirmo": "on"}, follow=True)
        self.assertIn("Reembolso de R$ 2.156", self.texto(resposta))
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, "cancelado")
        registro = Cancelamento.objects.get(contrato=contrato)
        self.assertEqual(registro.percentual_reembolso, 70)
        self.assertEqual(float(registro.valor_artista), 924)
        linhas = []
        for pagamento in contrato.pagamentos.order_by("valor"):
            linhas.append((pagamento.status, float(pagamento.valor)))
        self.assertEqual(linhas, [("liberado", 924.0), ("reembolsado", 2156.0)])
        self.assertIn("cancelou o evento", self.notificacoes_de("neonsombra")[0].texto)

    def test_cancelar_contrato_ainda_nao_pago_nao_cobra_nada(self):
        contrato = self.aceitar_selva()
        self.client.post("/contratos/" + str(contrato.id) + "/cancelar", {"motivo": "Mudamos de ideia", "confirmo": "on"})
        self.assertEqual(contrato.pagamentos.count(), 0)
        self.assertEqual(float(Cancelamento.objects.get(contrato=contrato).valor_reembolso), 0)
        # a data volta a ficar livre na agenda do artista
        self.assertFalse(Disponibilidade.objects.filter(artista=self.artista("Selva Ritmo"),
                                                        data=date(2026, 12, 12)).exists())

    def test_cancelamento_exige_motivo_e_confirmacao(self):
        contrato = self.contrato("luiz", "Neon Sombra")
        Contrato.objects.filter(id=contrato.id).update(data_evento=date.today() + timedelta(days=20))
        self.entrar("luiz")
        url = "/contratos/" + str(contrato.id) + "/cancelar"
        self.assertEqual(self.client.post(url, {"motivo": "x", "confirmo": "on"}).status_code, 400)
        self.assertEqual(self.client.post(url, {"motivo": "Motivo válido"}).status_code, 400)
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, "valor_retido")

    def test_nao_cancela_evento_que_ja_passou(self):
        self.entrar("luiz")
        url = "/contratos/" + str(self.contrato("luiz", "Risada Tardia").id) + "/cancelar"
        self.assertIn("não pode ser cancelado", self.texto(self.client.get(url, follow=True)))

    def test_artista_cancela_reembolsa_tudo_e_reabre_o_pedido(self):
        contrato = self.aceitar_selva()
        self.client.post("/contratos/" + str(contrato.id) + "/pagar", {"metodo": "pix", "ciente": "on"})
        self.entrar("selvaritmo")
        resposta = self.client.post("/artista/contratos/" + str(contrato.id) + "/cancelar",
                                    {"motivo": "Problema de saúde na equipe"}, follow=True)
        self.assertIn("cliente reembolsado em R$ 2.800", self.texto(resposta))
        self.assertEqual(contrato.pagamentos.get().status, "reembolsado")
        self.assertEqual(self.pedido("luiz").status, "aberto")
        self.assertIn("100% de volta", self.notificacoes_de("luiz")[0].texto)

    def test_artista_nao_cancela_contrato_de_outro(self):
        contrato = self.contrato("luiz", "Neon Sombra")
        self.entrar("selvaritmo")
        self.client.post("/artista/contratos/" + str(contrato.id) + "/cancelar", {"motivo": "Tentando cancelar"})
        contrato.refresh_from_db()
        self.assertEqual(contrato.status, "valor_retido")


# ---------------------------------------------------------------
# Favoritos
# ---------------------------------------------------------------
class TestFavoritos(BaseArtConnect):

    def test_cliente_salva_e_remove_favorito(self):
        self.entrar("luiz")
        url = "/artistas/" + str(self.artista("Mestre Ilusão").id) + "/favorito"
        self.client.post(url)
        painel = self.texto(self.client.get("/painel?aba=favoritos"))
        self.assertIn("Mestre Ilusão", painel)
        self.assertIn("Clara Veloso", painel)
        self.assertIn("Salvo nos favoritos",
                      self.texto(self.client.get("/artistas/" + str(self.artista("Mestre Ilusão").id))))

        resposta = self.client.post(url, follow=True)
        self.assertIn("saiu dos seus favoritos", self.texto(resposta))
        self.assertEqual(Favorito.objects.count(), 2)

    def test_artista_nao_tem_favoritos(self):
        self.entrar("selvaritmo")
        resposta = self.client.post("/artistas/" + str(self.artista("Mestre Ilusão").id) + "/favorito", follow=True)
        self.assertIn("Só clientes", self.texto(resposta))
        self.assertEqual(Favorito.objects.count(), 2)


# ---------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------
class TestNotificacoes(BaseArtConnect):

    def test_sino_mostra_quantidade_e_abrir_marca_como_lida(self):
        self.entrar("luiz")
        self.assertIn("Notificações (3 novas)", self.texto(self.client.get("/")))
        aviso = self.notificacoes_de("luiz")[0]
        resposta = self.client.post("/notificacoes/" + str(aviso.id) + "/abrir")
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta["Location"].endswith(aviso.link))
        aviso.refresh_from_db()
        self.assertTrue(aviso.lida)

        self.client.post("/notificacoes/ler-todas")
        self.assertEqual(Notificacao.objects.filter(user__username="luiz", lida=False).count(), 0)

    def test_nao_abre_notificacao_de_outra_pessoa(self):
        aviso = self.notificacoes_de("luiz")[0]
        self.entrar("helena")
        resposta = self.client.post("/notificacoes/" + str(aviso.id) + "/abrir", follow=True)
        self.assertIn("Notificação não encontrada", self.texto(resposta))
        aviso.refresh_from_db()
        self.assertFalse(aviso.lida)

    def test_proposta_nova_gera_notificacao_para_o_cliente(self):
        self.entrar("selvaritmo")
        Disponibilidade.objects.filter(data=date(2026, 12, 5)).delete()
        self.client.post("/artista/pedidos/" + str(self.pedido("rafael").id) + "/responder",
                         {"acao": "proposta", "valor": "3000"})
        self.assertEqual(self.notificacoes_de("rafael")[0].texto, "Selva Ritmo enviou uma proposta de R$ 3.000.")


# ---------------------------------------------------------------
# Conversa no contrato
# ---------------------------------------------------------------
class TestConversa(BaseArtConnect):

    def test_conversa_marca_lidas_e_envia_mensagem(self):
        contrato = self.contrato("luiz", "Selva Ritmo")
        url = "/contratos/" + str(contrato.id) + "/conversa"
        self.entrar("luiz")
        self.assertIn("Vocês têm som no local", self.texto(self.client.get(url)))
        self.assertEqual(contrato.mensagens.filter(lida=False).count(), 0)

        self.client.post(url, {"conteudo": "Temos som, pode vir só com o controlador."})
        self.entrar("selvaritmo")
        self.assertIn("pode vir só com o controlador", self.texto(self.client.get(url)))
        self.assertEqual(self.notificacoes_de("selvaritmo")[0].tipo, "mensagem")

    def test_conversa_e_privada(self):
        self.entrar("helena")
        url = "/contratos/" + str(self.contrato("luiz", "Selva Ritmo").id) + "/conversa"
        self.assertIn("Conversa não encontrada", self.texto(self.client.get(url, follow=True)))

    def test_nao_envia_mensagem_para_artista_sem_conta(self):
        contrato = self.contrato("luiz", "Estúdio Lume")
        self.entrar("luiz")
        self.client.post("/contratos/" + str(contrato.id) + "/conversa", {"conteudo": "Oi!"})
        self.assertEqual(contrato.mensagens.count(), 0)


# ---------------------------------------------------------------
# Denúncias e moderação
# ---------------------------------------------------------------
class TestDenuncias(BaseArtConnect):

    def avaliacao_do_rafael(self):
        return Avaliacao.objects.get(cliente__username="rafael")

    def test_denuncia_de_avaliacao_procedente_esconde_e_recalcula_nota(self):
        self.entrar("helena")
        dados = {"alvo": "avaliacao", "alvo_id": str(self.avaliacao_do_rafael().id), "motivo": "falso"}
        self.client.post("/denunciar", dados)
        resposta = self.client.post("/denunciar", dados, follow=True)
        self.assertIn("já denunciou", self.texto(resposta))

        self.entrar("admin")
        self.assertIn("Banda muito bem ensaiada", self.texto(self.client.get("/admin/denuncias")))
        denuncia = Denuncia.objects.get()
        self.client.post("/admin/denuncias/" + str(denuncia.id) + "/decidir",
                         {"decisao": "procedente", "justificativa": "Cliente não reconheceu o evento"})

        self.assertTrue(self.avaliacao_do_rafael().oculta)
        perfil = self.texto(self.client.get("/artistas/" + str(self.artista("Coletivo Maré").id)))
        self.assertNotIn("Banda muito bem ensaiada", perfil)
        self.assertEqual(Artista.objects.com_nota().get(nome_artistico="Coletivo Maré").total_avaliacoes, 0)
        self.assertIn("conteúdo foi removido", self.notificacoes_de("helena")[0].texto)

    def test_denuncia_improcedente_mantem_conteudo(self):
        self.entrar("helena")
        self.client.post("/denunciar", {"alvo": "avaliacao", "alvo_id": str(self.avaliacao_do_rafael().id),
                                        "motivo": "ofensivo"})
        self.entrar("admin")
        self.client.post("/admin/denuncias/" + str(Denuncia.objects.get().id) + "/decidir",
                         {"decisao": "improcedente", "justificativa": "Crítica educada"})
        self.assertFalse(self.avaliacao_do_rafael().oculta)
        self.assertEqual(Denuncia.objects.get().status, "improcedente")

    def test_perfil_suspenso_some_da_busca_e_pode_voltar(self):
        mestre = self.artista("Mestre Ilusão")
        self.entrar("luiz")
        self.client.post("/denunciar", {"alvo": "artista", "alvo_id": str(mestre.id), "motivo": "golpe",
                                        "detalhes": "Pediu pagamento por fora"})
        self.entrar("admin")
        self.client.post("/admin/denuncias/" + str(Denuncia.objects.get().id) + "/decidir",
                         {"decisao": "procedente", "justificativa": "Pedido de pagamento por fora confirmado"})
        self.client.logout()
        self.assertNotIn("Mestre Ilusão", self.texto(self.client.get("/")))
        self.assertIn("Artista não encontrado",
                      self.texto(self.client.get("/artistas/" + str(mestre.id), follow=True)))

        self.entrar("admin")
        self.client.post("/admin/artistas/" + str(mestre.id) + "/reativar")
        self.client.logout()
        self.assertIn("Mestre Ilusão", self.texto(self.client.get("/")))

    def test_so_admin_decide_denuncia(self):
        self.entrar("helena")
        self.client.post("/denunciar", {"alvo": "avaliacao", "alvo_id": str(self.avaliacao_do_rafael().id),
                                        "motivo": "spam"})
        self.client.post("/admin/denuncias/" + str(Denuncia.objects.get().id) + "/decidir",
                         {"decisao": "procedente", "justificativa": "Tentando sozinha"})
        self.assertEqual(Denuncia.objects.get().status, "aberta")


# ---------------------------------------------------------------
# Portfólio
# ---------------------------------------------------------------
class TestPortfolio(BaseArtConnect):

    def test_artista_adiciona_video_que_aparece_no_perfil(self):
        self.entrar("selvaritmo")
        self.client.post("/artista/portfolio", {"tipo": "video", "titulo": "Set completo",
                                                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        perfil = self.texto(self.client.get("/artistas/" + str(self.artista("Selva Ritmo").id)))
        self.assertIn("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", perfil)
        self.assertIn("Set no casamento do Jardim Ipê", perfil)

    def test_portfolio_valida_links(self):
        self.entrar("selvaritmo")
        resposta = self.client.post("/artista/portfolio", {"tipo": "foto", "titulo": "Foto",
                                                           "url": "http://inseguro.com/a.jpg"}, follow=True)
        self.assertIn("https://", self.texto(resposta))
        resposta = self.client.post("/artista/portfolio", {"tipo": "video", "titulo": "Vídeo",
                                                           "url": "https://exemplo.com/video.mp4"}, follow=True)
        self.assertIn("YouTube ou do Vimeo", self.texto(resposta))
        self.assertEqual(Portfolio.objects.filter(artista=self.artista("Selva Ritmo")).count(), 1)

    def test_artista_so_remove_o_proprio_item(self):
        item = Portfolio.objects.get(artista__nome_artistico="Neon Sombra")
        self.entrar("selvaritmo")
        self.client.post("/artista/portfolio/" + str(item.id) + "/remover")
        self.assertTrue(Portfolio.objects.filter(id=item.id).exists())
        self.entrar("neonsombra")
        self.client.post("/artista/portfolio/" + str(item.id) + "/remover")
        self.assertFalse(Portfolio.objects.filter(id=item.id).exists())


# ---------------------------------------------------------------
# Senhas das contas da versão anterior (Flask)
# ---------------------------------------------------------------
class TestSenhaVersaoAnterior(TestCase):

    def test_conta_antiga_entra_com_a_mesma_senha(self):
        import hashlib
        from django.contrib.auth.hashers import check_password
        from ArtConnect.hashers import converter_senha_werkzeug
        # mesmo formato que o Werkzeug (Flask) gerava
        salt = "AbCdEfGh12345678"
        hash_hex = hashlib.scrypt(b"minhasenha1", salt=salt.encode(), n=32768, r=8, p=1,
                                  maxmem=132 * 32768 * 8).hex()
        antigo = "scrypt:32768:8:1$" + salt + "$" + hash_hex
        convertido = converter_senha_werkzeug(antigo)
        self.assertLessEqual(len(convertido), 128)
        self.assertTrue(check_password("minhasenha1", convertido))
        self.assertFalse(check_password("outrasenha", convertido))


# ===============================================================
# Sprint 8
# ===============================================================
class TestSelos(BaseArtConnect):

    def codigos(self, nome):
        from ArtConnect.selos import codigos_dos_selos
        return codigos_dos_selos(Artista.objects.com_nota().get(nome_artistico=nome))

    def test_selos_calculados_pelas_regras(self):
        self.assertEqual(self.codigos("Selva Ritmo"), ["bem_avaliado", "responde_rapido", "confiavel", "perfil_completo"])
        self.assertEqual(self.codigos("Clara Veloso"), ["novo_talento"])

    def test_cancelar_tira_o_selo_confiavel(self):
        contrato = self.contrato("luiz", "Selva Ritmo")
        Cancelamento.objects.create(contrato=contrato, cancelado_por="artista", motivo="Imprevisto",
                                    dias_antecedencia=3, percentual_reembolso=100)
        self.assertNotIn("confiavel", self.codigos("Selva Ritmo"))

    def test_selos_aparecem_no_perfil_e_na_home(self):
        perfil = self.texto(self.client.get("/artistas/" + str(self.artista("Selva Ritmo").id)))
        self.assertIn("Responde rápido", perfil)
        self.assertIn("Perfil completo", perfil)
        self.assertIn("✦ Novo talento", self.texto(self.client.get("/")))


class TestCupom(BaseArtConnect):

    def test_desconto_tem_teto_de_metade_do_contrato(self):
        from ArtConnect.politicas import calcular_desconto
        self.assertEqual(calcular_desconto("percentual", 10, 2800, 300), 280)
        self.assertEqual(calcular_desconto("percentual", 20, 2800, 300), 300)
        self.assertEqual(calcular_desconto("fixo", 900, 1000), 500)

    def test_pagamento_com_cupom(self):
        contrato = self.aceitar_selva()
        url = "/contratos/" + str(contrato.id) + "/pagar"
        pagina = self.texto(self.client.get(url + "?cupom=bemvindo10"))
        self.assertIn("desconto de R$ 280", pagina)
        self.assertIn("Confirmar pagamento de R$ 2.520", pagina)

        self.client.post(url, {"metodo": "pix", "ciente": "on", "cupom": "BEMVINDO10"})
        pagamento = contrato.pagamentos.get()
        self.assertEqual(pagamento.status, "retido")
        self.assertEqual(float(pagamento.valor), 2520)
        self.assertEqual(float(pagamento.desconto), 280)
        self.assertEqual(pagamento.cupom.codigo, "BEMVINDO10")

    def test_cupom_vencido_ou_inexistente_nao_paga(self):
        contrato = self.aceitar_selva()
        url = "/contratos/" + str(contrato.id) + "/pagar"
        self.assertIn("venceu", self.texto(self.client.get(url + "?cupom=NATAL2025")))
        resposta = self.client.post(url, {"metodo": "pix", "ciente": "on", "cupom": "NAOEXISTE"})
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(contrato.pagamentos.get().status, "pendente")

    def test_cupom_abaixo_do_minimo_e_uso_unico(self):
        from ArtConnect.models import Cupom
        Cupom.objects.create(codigo="GRANDE", tipo="fixo", valor=100, valor_minimo=5000)
        contrato = self.aceitar_selva()
        url = "/contratos/" + str(contrato.id) + "/pagar"
        self.assertIn("a partir de R$ 5.000", self.texto(self.client.get(url + "?cupom=GRANDE")))
        # luiz já usou o ARTE50 em outro contrato
        outro = self.contrato("luiz", "Neon Sombra")
        Pagamento.objects.filter(contrato=outro).update(cupom=Cupom.objects.get(codigo="ARTE50"))
        self.assertIn("já usou", self.texto(self.client.get(url + "?cupom=ARTE50")))


class TestSuporte(BaseArtConnect):

    def abrir(self, **extra):
        dados = {"categoria": "pagamento", "assunto": "Reembolso não chegou",
                 "descricao": "Cancelei faz uma semana e o dinheiro não voltou."}
        dados.update(extra)
        return self.client.post("/suporte", dados)

    def test_abrir_chamado_com_prazo_da_categoria(self):
        self.entrar("helena")
        resposta = self.abrir()
        self.assertEqual(resposta.status_code, 302)
        chamado = ChamadoSuporte.objects.get(user__username="helena")
        horas = (chamado.prazo_resposta - chamado.criado_em).total_seconds() / 3600
        self.assertAlmostEqual(horas, 24, places=1)
        self.assertIn("Reembolso não chegou", self.texto(self.client.get("/suporte")))

    def test_chamado_invalido(self):
        self.entrar("helena")
        resposta = self.abrir(assunto="oi", categoria="xyz")
        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(ChamadoSuporte.objects.filter(user__username="helena").exists())

    def test_equipe_responde_e_usuario_resolve_e_reabre(self):
        self.entrar("helena")
        self.abrir()
        chamado = ChamadoSuporte.objects.get(user__username="helena")
        url = "/suporte/" + str(chamado.id)
        self.entrar("admin")
        self.assertIn("Reembolso não chegou", self.texto(self.client.get("/admin/suporte")))
        self.client.post(url, {"texto": "Já estamos verificando com o banco."})
        chamado.refresh_from_db()
        self.assertEqual(chamado.status, "em_andamento")
        self.assertEqual(self.notificacoes_de("helena")[0].tipo, "suporte")

        self.entrar("helena")
        self.client.post(url, {"acao": "resolver"})
        chamado.refresh_from_db()
        self.assertEqual(chamado.status, "resolvido")
        self.client.post(url, {"texto": "Voltou a dar erro."})
        chamado.refresh_from_db()
        self.assertEqual(chamado.status, "aberto")

    def test_chamado_e_privado(self):
        chamado = ChamadoSuporte.objects.get(user__username="luiz")
        self.entrar("helena")
        resposta = self.client.get("/suporte/" + str(chamado.id), follow=True)
        self.assertIn("Chamado não encontrado", self.texto(resposta))

    def test_chamado_atrasado(self):
        from ArtConnect.views import chamado_atrasado
        self.entrar("helena")
        self.abrir()
        chamado = ChamadoSuporte.objects.get(user__username="helena")
        self.assertFalse(chamado_atrasado(chamado))
        ChamadoSuporte.objects.filter(id=chamado.id).update(prazo_resposta=timezone.now() - timedelta(hours=1))
        chamado.refresh_from_db()
        self.assertTrue(chamado_atrasado(chamado))

    def test_so_admin_ve_a_fila(self):
        self.entrar("luiz")
        self.assertEqual(self.client.get("/admin/suporte").status_code, 302)


class TestRespostaAvaliacao(BaseArtConnect):

    def test_artista_responde_e_aparece_no_perfil(self):
        avaliacao = Avaliacao.objects.get(cliente__username="rafael")
        self.entrar("coletivomare")
        self.client.post("/artista/avaliacoes/" + str(avaliacao.id) + "/responder",
                         {"resposta": "Obrigado, Rafael! Vamos chegar mais cedo na próxima."})
        perfil = self.texto(self.client.get("/artistas/" + str(self.artista("Coletivo Maré").id)))
        self.assertIn("Vamos chegar mais cedo", perfil)
        self.assertIn("respondeu à sua avaliação", self.notificacoes_de("rafael")[0].texto)

    def test_artista_nao_responde_avaliacao_de_outro(self):
        avaliacao = Avaliacao.objects.get(cliente__username="rafael")
        self.entrar("selvaritmo")
        self.client.post("/artista/avaliacoes/" + str(avaliacao.id) + "/responder", {"resposta": "Tentando responder"})
        avaliacao.refresh_from_db()
        self.assertEqual(avaliacao.resposta, "")


class TestRelatorios(BaseArtConnect):

    def test_admin_baixa_csv(self):
        self.entrar("admin")
        resposta = self.client.get("/admin/relatorios/contratos.csv")
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/csv", resposta["Content-Type"])
        self.assertIn("attachment", resposta["Content-Disposition"])
        conteudo = resposta.content.decode("utf-8-sig")
        self.assertTrue(conteudo.startswith("codigo;cliente;artista"))
        self.assertIn("Selva Ritmo", conteudo)
        self.assertEqual(len(conteudo.strip().split("\n")), 9)   # cabeçalho + 8 contratos
        for tipo in ["pagamentos", "pedidos", "usuarios", "chamados"]:
            self.assertEqual(self.client.get("/admin/relatorios/" + tipo + ".csv").status_code, 200)

    def test_csv_so_para_admin(self):
        self.entrar("luiz")
        self.assertEqual(self.client.get("/admin/relatorios/contratos.csv").status_code, 302)


class TestComprovante(BaseArtConnect):

    def test_cliente_e_artista_veem_comprovante(self):
        contrato = self.contrato("luiz", "Selva Ritmo")
        url = "/contratos/" + str(contrato.id) + "/comprovante"
        self.entrar("luiz")
        pagina = self.texto(self.client.get(url))
        self.assertIn("Comprovante de contratação", pagina)
        self.assertIn("R$ 4.620", pagina)
        self.assertIn("Código de verificação", pagina)
        self.entrar("selvaritmo")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_outra_pessoa_nao_ve(self):
        contrato = self.contrato("luiz", "Selva Ritmo")
        self.entrar("helena")
        resposta = self.client.get("/contratos/" + str(contrato.id) + "/comprovante", follow=True)
        self.assertIn("Contrato não encontrado", self.texto(resposta))

    def test_comprovante_mostra_desconto_do_cupom(self):
        contrato = self.aceitar_selva()
        self.client.post("/contratos/" + str(contrato.id) + "/pagar", {"metodo": "pix", "ciente": "on", "cupom": "ARTE50"})
        pagina = self.texto(self.client.get("/contratos/" + str(contrato.id) + "/comprovante"))
        self.assertIn("cupom ARTE50", pagina)
        self.assertIn("− R$ 50", pagina)


class TestLembretes(BaseArtConnect):

    def test_lembrete_7_dias_e_vespera_sem_repetir(self):
        from ArtConnect.lembretes import gerar_lembretes
        contrato = self.contrato("luiz", "Neon Sombra")
        Contrato.objects.filter(id=contrato.id).update(data_evento=date.today() + timedelta(days=5))
        self.assertEqual(gerar_lembretes(), 2)            # cliente e artista
        self.assertEqual(gerar_lembretes(), 0)            # não repete
        self.assertIn("Faltam 5 dias", self.notificacoes_de("luiz")[0].texto)
        self.assertEqual(self.notificacoes_de("neonsombra")[0].tipo, "lembrete")

        Contrato.objects.filter(id=contrato.id).update(data_evento=date.today() + timedelta(days=1))
        self.assertEqual(gerar_lembretes(), 2)
        self.assertIn("Amanhã é o dia", self.notificacoes_de("luiz")[0].texto)

    def test_lembrete_aparece_ao_abrir_o_site(self):
        contrato = self.contrato("luiz", "Neon Sombra")
        Contrato.objects.filter(id=contrato.id).update(data_evento=date.today() + timedelta(days=3))
        self.entrar("luiz")
        self.client.get("/")
        self.assertEqual(self.notificacoes_de("luiz")[0].tipo, "lembrete")

    def test_comando_enviar_lembretes(self):
        from io import StringIO
        from django.core.management import call_command
        contrato = self.contrato("luiz", "Neon Sombra")
        Contrato.objects.filter(id=contrato.id).update(data_evento=date.today() + timedelta(days=2))
        saida = StringIO()
        call_command("enviar_lembretes", stdout=saida)
        self.assertIn("2 lembrete(s)", saida.getvalue())

    def test_evento_passado_ou_cancelado_nao_gera_lembrete(self):
        from ArtConnect.lembretes import gerar_lembretes
        Contrato.objects.filter(artista__nome_artistico="Neon Sombra").update(
            data_evento=date.today() + timedelta(days=2), status="cancelado")
        self.assertEqual(gerar_lembretes(), 0)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class TestPopularBancoAntigo(TestCase):
    def test_banco_sem_cupons_recebe_os_de_exemplo(self):
        from django.core.management import call_command
        popular(mostrar=False)
        Cupom.objects.all().delete()
        call_command("popular_banco", stdout=StringIO())
        self.assertTrue(Cupom.objects.filter(codigo="BEMVINDO10").exists())
        call_command("popular_banco", stdout=StringIO())
        self.assertEqual(Cupom.objects.filter(codigo="BEMVINDO10").count(), 1)
