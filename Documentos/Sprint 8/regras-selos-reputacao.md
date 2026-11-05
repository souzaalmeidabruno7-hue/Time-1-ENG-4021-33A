# Regras dos selos de reputação dos artistas

## Por que ter selos

A nota média sozinha não conta a história toda. Um artista com uma única avaliação 5,0 aparece igual a um que fez dezenas de eventos, e quem acabou de chegar fica sem nenhum destaque. Os selos resumem, em poucas palavras, o que o cliente mais quer saber antes de contratar: se o artista é **bem avaliado**, se **responde rápido**, se **cumpre o que combina** e se o **perfil está completo**.

Os selos são calculados automaticamente com dados do banco. Nem o artista nem a equipe podem dar um selo na mão, o que evita favorecimento.

## Os cinco selos

| Selo | Regra para ganhar | De onde vem o dado |
|---|---|---|
| Bem avaliado | Nota média **4,5 ou mais**, com pelo menos 1 avaliação visível | `avaliacoes.nota` (sem as ocultas pela moderação) |
| Responde rápido | Tempo médio entre o pedido chegar e o artista responder **até 24 horas** | `propostas.criado_em` − `pedidos_orcamento.criado_em` |
| Confiável | Pelo menos **1 contrato concluído** e **nenhum cancelamento pelo artista** nos últimos 12 meses | `contratos.status` e `cancelamentos.cancelado_por` |
| Perfil completo | Tem **descrição**, **estilo** e pelo menos **1 item no portfólio** | `artistas` e `portfolio` |
| Novo talento | Cadastrado há **até 60 dias** e **sem avaliações** ainda | `artistas.criado_em` |

## Regras gerais

- **O selo some sozinho** quando a regra deixa de valer. Por exemplo, o artista perde o "Confiável" no dia em que cancela um evento.
- **"Novo talento" e "Bem avaliado" nunca aparecem juntos**: assim que o artista recebe a primeira avaliação, ele deixa de ser novo.
- **Recusar um pedido também conta como resposta** no cálculo do "Responde rápido". O que importa é não deixar o cliente sem retorno.
- **Ordem de exibição:** Bem avaliado, Responde rápido, Confiável, Perfil completo, Novo talento.

## Onde os selos aparecem

| Tela | O que mostra |
|---|---|
| Perfil do artista | Todos os selos, com a explicação ao passar o mouse |
| Busca e destaques da home | Os 2 primeiros selos, para não poluir o card |

## Por que esses números

- **4,5:** a maioria dos marketplaces de serviço considera "excelente" a partir de 4,5. Abaixo disso, o selo perderia o valor.
- **24 horas:** quem organiza evento compara orçamentos em poucos dias. Uma resposta depois de 24 horas costuma chegar quando o cliente já decidiu.
- **12 meses:** dá uma segunda chance a quem teve um problema pontual há muito tempo.
- **60 dias:** é tempo suficiente para o artista fechar os primeiros contratos.

## Como isso aparece no sistema

| Regra | Onde está |
|---|---|
| Cálculo de cada selo | `artconnect-django/ArtConnect/selos.py` |
| Selos no perfil | `templates/artista.html` |
| Selos na busca e nos destaques | `templates/index.html` |
