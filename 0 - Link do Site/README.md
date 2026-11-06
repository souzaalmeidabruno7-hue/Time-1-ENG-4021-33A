# ArtConnect no ar

**Site:** https://artconnect-uoi0.onrender.com/

## Contas de teste

Todas usam a senha `artconnect123`.

| Usuário | Tipo | O que dá para ver |
|---|---|---|
| luiz | Cliente | Painel, pedidos, pagamento, cancelamento, favoritos, mensagens e notificações |
| selvaritmo | Artista | Painel do artista, propostas, agenda e portfólio |
| admin | Administrador | Dashboard, usuários e fila de denúncias |

## Criar conta

- O estado é escolhido numa lista com os 27 estados do Brasil.
- A data de nascimento é escolhida em três listas (dia, mês e ano). É preciso ter ao menos 18 anos para criar a conta.
- Quem tem menos de 18 anos não consegue entrar, mesmo com a senha certa.
- Quem escolhe "Ser contratado" (artista) também informa a cidade onde se apresenta, que a busca usa.

## Observações

- O site está no plano grátis do Render. Depois de 15 minutos sem acesso ele "dorme", e a primeira abertura pode levar uns 50 segundos.
- O banco grátis do Render expira 30 dias depois de criado. Antes disso, é preciso recriar o banco ou mudar de plano.
- O código do site (Django) está em `Documentos/artconnect-django/`, e a configuração do Render em `render.yaml`, na raiz do repositório.
- O admin do Django fica em `/django-admin/` (usuário `admin`).
