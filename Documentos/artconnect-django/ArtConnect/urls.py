"""
URL configuration for ArtConnect project.

Cada path() liga um endereço do site a uma função do views.py.
Os endereços são os mesmos da versão que já estava no ar.
"""

from django.contrib import admin
from django.urls import path

from ArtConnect import views

urlpatterns = [
    # admin do próprio Django (diferente do dashboard do site em /admin)
    path("django-admin/", admin.site.urls),

    # páginas públicas
    path("", views.index, name="index"),
    path("artistas/<str:artista_id>", views.artista_detalhe, name="artista_detalhe"),

    # conta
    path("login", views.entrar, name="login"),
    path("logout", views.sair, name="logout"),
    path("cadastro", views.cadastro, name="cadastro"),
    path("senha/esqueci", views.esqueci_senha, name="esqueci_senha"),
    path("senha/redefinir/<str:token>", views.redefinir_senha, name="redefinir_senha"),
    path("perfil/editar", views.editar_perfil, name="editar_perfil"),
    path("conta/excluir", views.excluir_conta, name="excluir_conta"),

    # cliente
    path("painel", views.painel, name="painel"),
    path("orcamento", views.orcamento, name="orcamento"),
    path("propostas/<str:proposta_id>/aceitar", views.aceitar_proposta, name="aceitar_proposta"),
    path("propostas/<str:proposta_id>/recusar", views.recusar_proposta, name="recusar_proposta"),
    path("contratos/<str:contrato_id>/confirmar", views.confirmar_evento, name="confirmar_evento"),
    path("contratos/<str:contrato_id>/avaliar", views.avaliar_contrato, name="avaliar_contrato"),
    path("contratos/<str:contrato_id>/pagar", views.pagar_contrato, name="pagar_contrato"),
    path("contratos/<str:contrato_id>/cancelar", views.cancelar_contrato, name="cancelar_contrato"),
    path("contratos/<str:contrato_id>/conversa", views.conversa, name="conversa"),
    path("artistas/<str:artista_id>/favorito", views.alternar_favorito, name="alternar_favorito"),

    # artista
    path("artista/painel", views.artista_painel, name="artista_painel"),
    path("artista/pedidos/<str:pedido_id>/responder", views.responder_pedido, name="responder_pedido"),
    path("artista/agenda", views.atualizar_agenda, name="atualizar_agenda"),
    path("artista/contratos/<str:contrato_id>/cancelar", views.artista_cancelar_contrato, name="artista_cancelar_contrato"),
    path("artista/portfolio", views.adicionar_portfolio, name="adicionar_portfolio"),
    path("artista/portfolio/<str:item_id>/remover", views.remover_portfolio, name="remover_portfolio"),

    # notificações e denúncias
    path("notificacoes", views.notificacoes, name="notificacoes"),
    path("notificacoes/ler-todas", views.ler_todas_notificacoes, name="ler_todas_notificacoes"),
    path("notificacoes/<str:notificacao_id>/abrir", views.abrir_notificacao, name="abrir_notificacao"),
    path("denunciar", views.denunciar, name="denunciar"),

    # administração do site
    path("admin", views.admin_dashboard, name="admin_dashboard"),
    path("usuarios", views.listar_usuarios, name="listar_usuarios"),
    path("admin/denuncias", views.admin_denuncias, name="admin_denuncias"),
    path("admin/denuncias/<str:denuncia_id>/decidir", views.decidir_denuncia, name="decidir_denuncia"),
    path("admin/artistas/<str:artista_id>/reativar", views.reativar_artista, name="reativar_artista"),
]

handler404 = "ArtConnect.views.pagina_nao_encontrada"
