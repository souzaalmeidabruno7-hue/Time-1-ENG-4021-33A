# Roteiro de testes de usabilidade

## Objetivo

Os testes automatizados mostram que o sistema **funciona**. Este roteiro serve para descobrir se ele é **fácil de usar** por quem nunca viu o site. A ideia é observar pessoas reais fazendo tarefas comuns, sem ajuda, e anotar onde elas travam.

## Participantes

| Perfil | Quantidade | Onde encontrar |
|---|---|---|
| Quem já organizou um evento (aniversário, casamento, formatura) | 3 | Família, amigos e as pessoas das entrevistas da Sprint 1 |
| Artista ou prestador de serviço | 2 | Músicos, fotógrafos e DJs conhecidos do grupo |

Cinco pessoas costumam ser suficientes para achar a maior parte dos problemas de uma tela.

## Preparação

- Usar o site no ar: https://artconnect-uoi0.onrender.com/
- Abrir o site uns minutos antes, porque o plano grátis do Render "dorme" e a primeira abertura demora.
- Contas de teste: `luiz` (cliente) e `selvaritmo` (artista), senha `artconnect123`. Quem for testar o cadastro cria uma conta nova.
- Um integrante conduz e outro só anota. Sempre que der, gravar a tela com autorização do participante.

## Como conduzir

1. Explicar que **quem está sendo testado é o site, não a pessoa**.
2. Pedir para **pensar em voz alta** enquanto usa.
3. Ler uma tarefa por vez e **não ajudar**. Se a pessoa travar por mais de 2 minutos, anotar e passar para a próxima.
4. No final, fazer as perguntas de fechamento.

## Tarefas do cliente

| # | Tarefa lida para o participante | Deu certo se… | Tempo esperado |
|---|---|---|---|
| 1 | "Você vai fazer uma festa no Rio com orçamento de R$ 2.500 em 12/12. Encontre um DJ que combine." | Usou a busca com cidade, orçamento e data e abriu um perfil | 2 min |
| 2 | "Salve esse artista para decidir depois." | Clicou em Salvar nos favoritos e achou o artista na aba Favoritos | 1 min |
| 3 | "Peça um orçamento para essa festa." | Enviou o formulário sem erro | 3 min |
| 4 | "Você recebeu propostas. Aceite a mais barata." | Achou a aba Pedidos e aceitou a proposta certa | 2 min |
| 5 | "Pague usando o cupom BEMVINDO10." | Aplicou o cupom e viu o desconto antes de pagar | 2 min |
| 6 | "Imprima o comprovante da contratação." | Achou o botão Comprovante | 1 min |
| 7 | "Algo deu errado com o pagamento. Peça ajuda." | Abriu um chamado na central de suporte | 2 min |

## Tarefas do artista

| # | Tarefa | Deu certo se… | Tempo esperado |
|---|---|---|---|
| 8 | "Você não pode trabalhar no dia 21/11. Marque isso." | Marcou a data como ocupada na agenda | 1 min |
| 9 | "Responda ao pedido de orçamento com R$ 3.000." | Enviou a proposta | 2 min |
| 10 | "Uma cliente te avaliou. Agradeça publicamente." | Respondeu à avaliação | 1 min |

## O que anotar em cada tarefa

| Campo | Exemplo |
|---|---|
| Concluiu? | Sim / Com dificuldade / Não |
| Tempo | 2min40s |
| Onde travou | "Procurou o cupom no resumo, e não no campo acima" |
| Frase marcante | "Ué, cadê o botão de pagar?" |

## Perguntas de fechamento

1. De 1 a 5, o quanto foi fácil usar o site?
2. Você confiaria em pagar por aqui? Por quê?
3. O que mais te confundiu?
4. O que você mudaria primeiro?
5. Usaria de novo no próximo evento?

## Como analisar

- **Taxa de sucesso por tarefa:** quantas pessoas concluíram sem ajuda. Toda tarefa abaixo de 80% vira um ajuste prioritário.
- **Gravidade de cada problema:** alta (impediu a tarefa), média (atrasou bastante) ou baixa (só incomodou).
- **Resultado:** cada problema alto ou médio vira um card no Kanban da sprint seguinte, com o link para este roteiro como evidência.

## Cuidados

- Pedir **autorização** antes de gravar, e não divulgar o nome dos participantes (LGPD).
- Não usar dados reais de cartão nem pagamento: o pagamento do site é uma simulação.
