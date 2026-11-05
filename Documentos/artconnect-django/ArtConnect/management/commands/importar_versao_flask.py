"""Copia os dados da versão anterior do site (Flask) para as tabelas do Django.

As duas versões usam o mesmo banco PostgreSQL no Render. A versão Flask tinha
tabelas com nomes como "profiles" e "artistas"; o Django usa "ArtConnect_artista",
"auth_user" etc. Este comando lê as tabelas antigas e grava tudo nas novas,
mantendo os mesmos códigos (ids), datas e senhas.

Só roda uma vez: se o Django já tiver dados, não faz nada.
Uso:  python manage.py importar_versao_flask
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from ArtConnect.hashers import converter_senha_werkzeug

from ArtConnect.models import (Artista, Avaliacao, Cancelamento, Categoria, ChamadoSuporte, Contrato, Denuncia,
                               Disponibilidade, Evento, Favorito, Mensagem, Notificacao, Pagamento, PedidoOrcamento,
                               Perfil, Portfolio, Proposta)


def tabela_existe(cursor, nome):
    cursor.execute("SELECT to_regclass(%s) IS NOT NULL", ["public." + nome])
    return cursor.fetchone()[0]


def coluna_existe(cursor, tabela, coluna):
    cursor.execute("SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                   [tabela, coluna])
    return cursor.fetchone() is not None


def linhas(cursor, tabela):
    """Lê todas as linhas de uma tabela antiga como dicionários (ou nenhuma, se a tabela não existir)."""
    if not tabela_existe(cursor, tabela):
        return []
    cursor.execute("SELECT * FROM " + tabela)
    nomes = []
    for coluna in cursor.description:
        nomes.append(coluna[0])
    resultado = []
    for valores in cursor.fetchall():
        resultado.append(dict(zip(nomes, valores)))
    return resultado


def texto(valor):
    if valor is None:
        return ""
    return valor


class Command(BaseCommand):
    help = "Copia os dados da versão Flask (mesmo banco) para as tabelas do Django, uma única vez."

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write("Banco não é PostgreSQL: não há versão anterior para importar.")
            return
        if Categoria.objects.exists() or User.objects.exists():
            self.stdout.write("O Django já tem dados. Importação não é necessária.")
            return
        with connection.cursor() as cursor:
            if not tabela_existe(cursor, "profiles"):
                self.stdout.write("Não há dados da versão anterior.")
                return
            with transaction.atomic():
                self.importar(cursor)

    def importar(self, cursor):
        # ---------- categorias (mantém os mesmos números) ----------
        for linha in linhas(cursor, "categorias"):
            Categoria.objects.create(id=linha["id"], nome=linha["nome"], slug=linha["slug"],
                                     descricao=texto(linha["descricao"]))
        cursor.execute("SELECT setval(pg_get_serial_sequence('\"ArtConnect_categoria\"', 'id'), "
                       "COALESCE((SELECT MAX(id) FROM \"ArtConnect_categoria\"), 1))")

        # ---------- contas: profiles -> User + Perfil ----------
        usuarios = {}   # id antigo (uuid) -> User novo
        for linha in linhas(cursor, "profiles"):
            admin = linha["papel"] == "admin"
            usuario = User.objects.create(username=linha["username"], email=linha["email"],
                                          password=converter_senha_werkzeug(linha["senha_hash"]), is_staff=admin, is_superuser=admin,
                                          date_joined=linha["criado_em"])
            perfil = Perfil.objects.create(user=usuario, nome=linha["nome"], telefone=texto(linha["telefone"]),
                                           cidade=texto(linha["cidade"]), papel=linha["papel"])
            Perfil.objects.filter(id=perfil.id).update(criado_em=linha["criado_em"])
            usuarios[linha["id"]] = usuario

        def conta(id_antigo):
            if id_antigo is None:
                return None
            return usuarios.get(id_antigo)

        # ---------- artistas ----------
        for linha in linhas(cursor, "artistas"):
            Artista.objects.create(id=linha["id"], user=conta(linha["user_id"]), nome_artistico=linha["nome_artistico"],
                                   categoria_id=linha["categoria_id"], estilo=texto(linha["estilo"]),
                                   cidade=linha["cidade"], preco_minimo=linha["preco_minimo"],
                                   descricao=texto(linha["descricao"]), foto_url=texto(linha["foto_url"]),
                                   ativo=linha["ativo"])
            Artista.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        # ---------- eventos e pedidos de orçamento ----------
        for linha in linhas(cursor, "eventos"):
            Evento.objects.create(id=linha["id"], cliente=conta(linha["cliente_id"]), tipo=linha["tipo"],
                                  categoria_id=linha["categoria_id"], data_evento=linha["data_evento"],
                                  localizacao=texto(linha["localizacao"]), orcamento=linha["orcamento"])
            Evento.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "pedidos_orcamento"):
            PedidoOrcamento.objects.create(id=linha["id"], evento_id=linha["evento_id"],
                                           categoria_id=linha["categoria_id"], data_evento=linha["data_evento"],
                                           horario_inicio=linha["horario_inicio"], duracao_horas=linha["duracao_horas"],
                                           estimativa_convidados=linha["estimativa_convidados"], local=linha["local"],
                                           observacoes=texto(linha["observacoes"]), status=linha["status"])
            PedidoOrcamento.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        # ---------- propostas, contratos e pagamentos ----------
        for linha in linhas(cursor, "propostas"):
            Proposta.objects.create(id=linha["id"], pedido_id=linha["pedido_id"], artista_id=linha["artista_id"],
                                    valor=linha["valor"], mensagem=texto(linha["mensagem"]),
                                    data_sugerida=linha.get("data_sugerida"), horario_sugerido=linha.get("horario_sugerido"),
                                    status=linha["status"])
            Proposta.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "contratos"):
            Contrato.objects.create(id=linha["id"], evento_id=linha["evento_id"], proposta_id=linha["proposta_id"],
                                    cliente=conta(linha["cliente_id"]), artista_id=linha["artista_id"],
                                    descricao=texto(linha["descricao"]), data_evento=linha["data_evento"],
                                    local=linha["local"], valor_total=linha["valor_total"], status=linha["status"])
            Contrato.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "pagamentos"):
            Pagamento.objects.create(id=linha["id"], contrato_id=linha["contrato_id"], valor=linha["valor"],
                                     metodo=texto(linha["metodo"]), status=linha["status"], pago_em=linha["pago_em"],
                                     liberado_em=linha["liberado_em"])
            Pagamento.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        # ---------- avaliações, mensagens, suporte e agenda ----------
        for linha in linhas(cursor, "avaliacoes"):
            Avaliacao.objects.create(id=linha["id"], contrato_id=linha["contrato_id"], artista_id=linha["artista_id"],
                                     cliente=conta(linha["cliente_id"]), nota=linha["nota"],
                                     comentario=linha["comentario"], oculta=linha.get("oculta", False))
            Avaliacao.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "mensagens"):
            Mensagem.objects.create(id=linha["id"], contrato_id=linha.get("contrato_id"),
                                    remetente=conta(linha["remetente_id"]), destinatario=conta(linha["destinatario_id"]),
                                    conteudo=linha["conteudo"], lida=linha["lida"], enviada_em=linha["enviada_em"])

        for linha in linhas(cursor, "chamados_suporte"):
            ChamadoSuporte.objects.create(id=linha["id"], user=conta(linha["user_id"]), assunto=linha["assunto"],
                                          descricao=linha["descricao"], status=linha["status"])
            ChamadoSuporte.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "disponibilidade"):
            Disponibilidade.objects.create(id=linha["id"], artista_id=linha["artista_id"], data=linha["data"],
                                           status=linha["status"], observacao=texto(linha["observacao"]))
            Disponibilidade.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        # ---------- tabelas da Sprint 7 (só existem se ela chegou a ser publicada) ----------
        for linha in linhas(cursor, "favoritos"):
            favorito = Favorito.objects.create(cliente=conta(linha["cliente_id"]), artista_id=linha["artista_id"])
            Favorito.objects.filter(id=favorito.id).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "notificacoes"):
            Notificacao.objects.create(id=linha["id"], user=conta(linha["user_id"]), tipo=linha["tipo"],
                                       texto=linha["texto"], link=texto(linha["link"]), lida=linha["lida"])
            Notificacao.objects.filter(id=linha["id"]).update(criada_em=linha["criada_em"])

        for linha in linhas(cursor, "cancelamentos"):
            Cancelamento.objects.create(id=linha["id"], contrato_id=linha["contrato_id"],
                                        cancelado_por=linha["cancelado_por"], motivo=linha["motivo"],
                                        dias_antecedencia=linha["dias_antecedencia"],
                                        percentual_reembolso=linha["percentual_reembolso"],
                                        valor_reembolso=linha["valor_reembolso"], valor_artista=linha["valor_artista"])
            Cancelamento.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        for linha in linhas(cursor, "denuncias"):
            Denuncia.objects.create(id=linha["id"], denunciante=conta(linha["denunciante_id"]),
                                    artista_id=linha["artista_id"], avaliacao_id=linha["avaliacao_id"],
                                    motivo=linha["motivo"], detalhes=texto(linha["detalhes"]), status=linha["status"],
                                    decisao=texto(linha["decisao"]), resolvida_em=linha["resolvida_em"])
            Denuncia.objects.filter(id=linha["id"]).update(criada_em=linha["criada_em"])

        for linha in linhas(cursor, "portfolio"):
            Portfolio.objects.create(id=linha["id"], artista_id=linha["artista_id"], tipo=linha["tipo"],
                                     titulo=linha["titulo"], url=linha["url"])
            Portfolio.objects.filter(id=linha["id"]).update(criado_em=linha["criado_em"])

        self.stdout.write("Importação concluída: " + str(len(usuarios)) + " contas, "
                          + str(Artista.objects.count()) + " artistas e "
                          + str(Contrato.objects.count()) + " contratos copiados da versão anterior.")
