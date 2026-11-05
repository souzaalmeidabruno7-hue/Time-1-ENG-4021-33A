> **Versão antiga (Flask).** O site atual foi refeito em Django, no formato pedido na disciplina, e está em [`Documentos/artconnect-django/`](../artconnect-django/). Esta pasta fica guardada porque os links de evidência das Sprints 6 e 7 apontam para cá.

# ArtConnect

Plataforma que conecta quem organiza eventos a artistas locais e independentes (DJs, mágicos, cantores, chefs, fotógrafos e mais).

Esta parte do projeto implementa as **views e rotas que renderizam as telas com conexão ao banco de dados**, usando Flask + PostgreSQL.

## Estrutura

```
artconnect/
├── app.py              # rotas (views) da aplicação
├── db.py               # conexão e funções de acesso ao banco
├── schema.sql          # criação das tabelas (modelo físico)
├── popular_banco.py    # cria as tabelas e insere dados de exemplo
├── match.py            # regras de pontuação da compatibilidade
├── tests/              # testes automatizados (pytest)
├── requirements.txt
├── .env.example
├── static/
│   └── style.css       # identidade visual compartilhada
└── templates/          # telas (HTML + Jinja)
    ├── base.html
    ├── index.html          # busca e listagem de artistas
    ├── artista.html        # perfil do artista
    ├── login.html          # login (username e password)
    ├── cadastro.html       # registro de usuário
    ├── painel.html         # painel do cliente
    ├── orcamento.html      # pedido de orçamento
    ├── perfil_editar.html  # edição de usuário
    ├── excluir.html        # remoção de usuário
    ├── usuarios.html       # listagem de usuários (admin)
    ├── painel_artista.html # painel do artista
    ├── avaliar.html        # avaliação pós-evento
    ├── esqueci_senha.html  # pedido de recuperação de senha
    ├── redefinir_senha.html# nova senha a partir do token
    ├── admin.html          # dashboard administrativo
    └── 404.html
```

## Rotas

| Rota | Método | O que faz | Tabelas usadas |
|---|---|---|---|
| `/` | GET | Lista artistas com filtro por categoria e cidade | `vw_artistas`, `categorias`, `avaliacoes` |
| `/artistas/<id>` | GET | Perfil do artista com depoimentos | `vw_artistas`, `avaliacoes` |
| `/login` | GET, POST | Login com usuário e senha | `profiles` |
| `/logout` | GET | Encerra a sessão | — |
| `/cadastro` | GET, POST | Registro de cliente ou artista | `profiles`, `artistas` |
| `/painel` | GET | Indicadores, histórico, pagamentos, pedidos e mensagens | `vw_painel_cliente`, `contratos`, `pagamentos`, `pedidos_orcamento`, `mensagens` |
| `/orcamento` | GET, POST | Envia um pedido de orçamento | `eventos`, `pedidos_orcamento` |
| `/perfil/editar` | GET, POST | Edita os dados do usuário logado | `profiles` |
| `/conta/excluir` | GET, POST | Remove a conta (bloqueia se houver pagamento retido) | `profiles`, `pagamentos` |
| `/usuarios` | GET | Lista e filtra usuários (só administrador) | `profiles` |
| `/?cidade=&orcamento=&data=` | GET | Busca ordenada por compatibilidade (match) | `vw_artistas`, `disponibilidade`, `contratos` |
| `/propostas/<id>/aceitar` | POST | Cliente aceita proposta e gera contrato | `propostas`, `pedidos_orcamento`, `contratos`, `pagamentos`, `disponibilidade` |
| `/propostas/<id>/recusar` | POST | Cliente recusa proposta | `propostas` |
| `/contratos/<id>/confirmar` | POST | Cliente confirma o evento e libera o pagamento | `contratos`, `pagamentos` |
| `/contratos/<id>/avaliar` | GET, POST | Cliente avalia o artista após o evento | `avaliacoes` |
| `/artista/painel` | GET | Painel do artista: pedidos, propostas, agenda e avaliações | `pedidos_orcamento`, `propostas`, `contratos`, `disponibilidade`, `avaliacoes` |
| `/artista/pedidos/<id>/responder` | POST | Artista envia proposta, contraproposta ou recusa | `propostas`, `pedidos_orcamento` |
| `/artista/agenda` | POST | Artista marca ou libera datas | `disponibilidade` |
| `/senha/esqueci` | GET, POST | Envia link de recuperação por e-mail | `profiles`, `tokens_senha` |
| `/senha/redefinir/<token>` | GET, POST | Valida o token e troca a senha | `tokens_senha`, `profiles` |
| `/admin` | GET | Dashboard com estatísticas de uso (só administrador) | todas |

As senhas são guardadas com hash (`werkzeug.security`) e todas as consultas usam parâmetros (`%s`), o que evita SQL injection.

## Como rodar (Codespaces ou máquina local)

1. Instalar as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Ter um banco PostgreSQL. Duas opções:
   - **Supabase:** crie um projeto e copie a connection string em *Project Settings › Database*.
   - **Local / Codespaces:**
     ```bash
     sudo apt-get update && sudo apt-get install -y postgresql
     sudo service postgresql start
     sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
     sudo -u postgres createdb artconnect
     ```

3. Criar o arquivo `.env` a partir do exemplo e colocar a URL do banco:
   ```bash
   cp .env.example .env
   ```
   Exemplo (banco local): `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/artconnect`

4. Criar as tabelas e popular o banco:
   ```bash
   python popular_banco.py
   ```

5. Rodar a aplicação:
   ```bash
   python app.py
   ```
   Acesse `http://localhost:5000` (no Codespaces, abra a aba **Portas** e clique na porta 5000).

## Testes automatizados

Os testes usam um banco separado, que é apagado e recriado a cada teste:

```bash
sudo -u postgres createdb artconnect_teste
pip install pytest
pytest
```

Para usar outro endereço: `TEST_DATABASE_URL=postgresql://... pytest`. Os dados de exemplo usam pedidos com datas até dezembro de 2026; depois disso, atualize as datas no `popular_banco.py`.

## E-mail de recuperação de senha

Sem configuração, o link aparece no terminal onde o `python app.py` está rodando. Para enviar de verdade, preencha `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA` e `SMTP_REMETENTE` no `.env`.

## Usuários de teste

Todos com a senha `artconnect123`:

| Usuário | Tipo |
|---|---|
| `luiz` | cliente (com contratos, pagamentos e mensagens) |
| `helena`, `rafael` | clientes |
| `selvaritmo`, `coletivomare`, `neonsombra` | artistas |
| `admin` | administrador (acessa `/usuarios`) |

> Rodar `python popular_banco.py` de novo apaga e recria todas as tabelas.
