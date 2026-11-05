from django.contrib import admin

# Register your models here.
# Tudo o que está registrado aqui pode ser visto e editado em /django-admin/

from ArtConnect.models import (Artista, Avaliacao, Cancelamento, Categoria, ChamadoSuporte, Contrato,
                               Denuncia, Disponibilidade, Evento, Favorito, Mensagem, Notificacao,
                               Pagamento, PedidoOrcamento, Perfil, Portfolio, Proposta)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ["nome", "user", "papel", "cidade", "criado_em"]
    list_filter = ["papel"]
    search_fields = ["nome", "user__username", "user__email"]


@admin.register(Artista)
class ArtistaAdmin(admin.ModelAdmin):
    list_display = ["nome_artistico", "categoria", "cidade", "preco_minimo", "ativo"]
    list_filter = ["categoria", "ativo"]
    search_fields = ["nome_artistico", "cidade"]


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ["artista", "cliente", "data_evento", "valor_total", "status"]
    list_filter = ["status"]


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ["motivo", "denunciante", "artista", "avaliacao", "status", "criada_em"]
    list_filter = ["status", "motivo"]


admin.site.register(Categoria)
admin.site.register(Evento)
admin.site.register(PedidoOrcamento)
admin.site.register(Proposta)
admin.site.register(Pagamento)
admin.site.register(Avaliacao)
admin.site.register(Mensagem)
admin.site.register(ChamadoSuporte)
admin.site.register(Disponibilidade)
admin.site.register(Favorito)
admin.site.register(Notificacao)
admin.site.register(Cancelamento)
admin.site.register(Portfolio)
