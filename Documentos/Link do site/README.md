# ArtConnect no ar

**Site:** https://artconnect-uoi0.onrender.com/

## Contas de teste

Todas usam a senha `artconnect123`.

| Usuário | Tipo | O que dá para ver |
|---|---|---|
| luiz | Cliente | Painel, pedidos, pagamento, cancelamento, favoritos, mensagens e notificações |
| selvaritmo | Artista | Painel do artista, propostas, agenda e portfólio |
| admin | Administrador | Dashboard, usuários e fila de denúncias |

## Observações

- O site está no plano grátis do Render. Depois de 15 minutos sem acesso ele "dorme", e a primeira abertura pode levar uns 50 segundos.
- O banco grátis do Render expira 30 dias depois de criado. Antes disso, é preciso recriar o banco ou mudar de plano.
- O código do site (Django) está em `Documentos/artconnect-django/`, e a configuração do Render em `render.yaml`, na raiz do repositório.
- O admin do Django fica em `/django-admin/` (usuário `admin`).
