# Categorias e prazos de atendimento do suporte

## Por que definir prazos

Num marketplace com pagamento retido, um problema sem resposta trava dinheiro de alguém. Por isso cada chamado tem uma **categoria**, e cada categoria tem um **prazo para a primeira resposta da equipe**. O sistema calcula o prazo sozinho e marca o chamado como **atrasado** quando ele passa.

## Categorias

| Categoria | Exemplos | Prazo da 1ª resposta | Por que esse prazo |
|---|---|---|---|
| Pagamento ou reembolso | Pagamento não confirmado, reembolso que não chegou, valor errado | **24 horas** | Envolve dinheiro retido |
| Problema com um contrato | Artista não respondeu, mudança de data, evento que não aconteceu | **24 horas** | Pode haver evento próximo |
| Conta e acesso | Não consigo entrar, trocar e-mail, excluir conta | **48 horas** | Existe a recuperação de senha automática |
| Erro no site | Página com erro, botão que não funciona | **48 horas** | Precisa de investigação técnica |
| Dúvida geral | Como funciona a retenção, como virar artista | **72 horas** | Não trava nenhum processo |

## Ciclo de vida do chamado

| Status | Quando acontece |
|---|---|
| Aberto | O usuário abre o chamado, ou escreve de novo num chamado já resolvido |
| Em andamento | A equipe responde pela primeira vez |
| Resolvido | O usuário ou a equipe marca como resolvido |

**Atrasado** não é um status, é um aviso. Ele aparece quando o chamado não está resolvido, a equipe ainda não respondeu e o prazo já passou.

## Regras de atendimento

- **Fila ordenada por prazo:** a equipe vê primeiro o chamado que vence antes, não o mais antigo.
- **Contrato vinculado:** o usuário pode escolher o contrato relacionado ao abrir o chamado, e a equipe já vê artista e data sem precisar perguntar.
- **Toda resposta da equipe gera uma notificação** no sino do usuário.
- **Prioridade sobre o prazo:** se o problema for de um evento nas próximas 48 horas, a equipe responde antes de qualquer outro chamado, mesmo que o prazo dele seja maior.
- **Nada de pagamento por fora:** a equipe nunca pede dados de cartão ou senha pelo chamado.

## Indicadores acompanhados

| Indicador | Meta |
|---|---|
| Chamados respondidos dentro do prazo | 90% |
| Chamados atrasados ao mesmo tempo | no máximo 3 |
| Chamados reabertos depois de resolvidos | menos de 10% |

O relatório de chamados (CSV) no dashboard do administrador traz os dados para medir esses indicadores.

## Como isso aparece no sistema

| Regra | Onde está |
|---|---|
| Categorias e prazos | `artconnect-django/ArtConnect/models.py` (`CATEGORIAS_SUPORTE` e `PRAZOS_SUPORTE`) |
| Abertura e conversa | `views.py` (rotas `suporte` e `chamado`) |
| Fila da equipe | `views.py` (rota `admin_suporte`) e `templates/admin_suporte.html` |
