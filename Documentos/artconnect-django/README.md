# ArtConnect (Django)

Marketplace que conecta quem organiza eventos a artistas e prestadores de serviço locais (música, gastronomia, entretenimento, foto e vídeo).

**Site no ar:** https://artconnect-uoi0.onrender.com/

O projeto segue o formato dos exemplos da disciplina: um projeto Django em que o pacote `ArtConnect/` tem as configurações, os modelos e as telas.

## Como rodar no computador (ou no Codespace)

```bash
cd Documentos/artconnect-django
pip install -r requirements.txt
python manage.py migrate          # cria as tabelas (banco SQLite: db.sqlite3)
python manage.py popular_banco    # coloca os dados de exemplo
python manage.py runserver
```

Depois abra http://127.0.0.1:8000.

## Contas de teste

Todas usam a senha `artconnect123`.

| Usuário | Tipo |
|---|---|
| luiz | Cliente |
| selvaritmo | Artista |
| admin | Administrador (também entra no admin do Django em `/django-admin/`) |

## Testes

```bash
python manage.py test
```

## Onde está cada coisa

| Arquivo | O que tem |
|---|---|
| `ArtConnect/models.py` | Tabelas do banco (ORM do Django) |
| `ArtConnect/views.py` | Uma função para cada tela ou ação |
| `ArtConnect/urls.py` | Endereços do site ligados às views |
| `ArtConnect/templates/` | Telas em HTML |
| `ArtConnect/templatetags/artconnect.py` | Filtros (moeda, datas) e componentes visuais (selo, estrelas, abas) |
| `ArtConnect/admin.py` | Tabelas que aparecem no admin do Django |
| `ArtConnect/match.py` | Cálculo do match de compatibilidade |
| `ArtConnect/politicas.py` | Regras de reembolso e de links de vídeo |
| `ArtConnect/dados_exemplo.py` | Dados de exemplo usados pelo `popular_banco` e pelos testes |
| `ArtConnect/tests.py` | Testes automatizados |
| `ArtConnect/static/` | CSS (Tailwind compilado) e fotos |

## Publicação no Render

O arquivo `render.yaml`, na raiz do repositório, publica esta pasta. Em produção, o Django usa o PostgreSQL indicado na variável `DATABASE_URL`. No computador, usa o SQLite.

## Visual (Tailwind)

O CSS final é `ArtConnect/static/style.css`, e ele já vai pronto no repositório. Só precisa compilar de novo se você usar uma classe do Tailwind que ainda não existe no site. A fonte do CSS está em `ArtConnect/static/src/input.css`.
