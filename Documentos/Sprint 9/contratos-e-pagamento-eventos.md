# Práticas de contrato e pagamento no mercado de eventos

**Sprint 9 · Tarefa difícil**

Como o mercado de eventos costuma fechar contratos, cobrar sinal e lidar com cancelamento, e o que a lei brasileira diz sobre isso. Compara essas práticas com as regras do ArtConnect, para ver se o site está alinhado com o mercado e com a lei.

## Como o mercado costuma fazer

| Prática | Como funciona no dia a dia |
|---|---|
| **Orçamento** | O fornecedor manda o preço com o que está incluído (horas, equipe, equipamento). |
| **Sinal para reservar a data** | O cliente paga uma parte na hora de fechar e o resto mais perto do evento ou no dia. A porcentagem varia de fornecedor para fornecedor. |
| **Contrato escrito** | Data, horário, local, serviço, valor, forma de pagamento e regras de cancelamento. |
| **Multa por cancelamento** | Muitos contratos preveem multa ou perda do sinal se o cliente desistir. |
| **Hora extra** | Tempo além do combinado é cobrado à parte. |

O problema comum: muita contratação é combinada só por mensagem, sem contrato claro, e o cliente paga direto ao fornecedor, sem garantia nenhuma.

## O que a lei diz

### Sinal (arras): Código Civil, art. 417 a 420

- O sinal confirma o contrato.
- Se **quem pagou o sinal desistir**, pode perder o sinal.
- Se **quem recebeu o sinal desistir**, tem que devolver o sinal **em dobro** (art. 418).
- O contrato pode prever **direito de arrependimento**; nesse caso, o sinal funciona como indenização e não cabe outra cobrança (art. 420).

### Código de Defesa do Consumidor (CDC)

- **Art. 49:** quem contrata **fora do estabelecimento** (internet, telefone) pode desistir em até **7 dias** e receber tudo de volta. A Justiça já aplicou essa regra a contratos fechados por WhatsApp.
- **Art. 51:** cláusulas que colocam o consumidor em **desvantagem exagerada** são abusivas e podem ser anuladas, como uma multa muito alta.

### Quando ninguém tem culpa

Na pandemia, o TJ-SP decidiu que um buffet tinha que **devolver o valor pago** por uma festa de casamento que não pôde acontecer por causa da quarentena. Como não houve culpa de nenhum dos lados, **a multa do contrato não valia** (Código Civil, art. 408).

## Comparação com o ArtConnect

| Situação | Prática comum / lei | ArtConnect hoje |
|---|---|---|
| Onde fica o dinheiro | Normalmente vai direto ao fornecedor | **Fica retido na plataforma** até o cliente confirmar o evento |
| Artista cancela | Lei: devolver o sinal em dobro | O cliente recebe **100% de volta** |
| Cliente cancela com 30 dias ou mais | Varia por contrato | **100%** de volta |
| Cliente cancela de 15 a 29 dias antes | Varia | **70%** de volta |
| Cliente cancela de 7 a 14 dias antes | Varia | **50%** de volta |
| Cliente cancela com menos de 7 dias | Varia | **0%** (o artista fica com o valor) |
| Arrependimento logo após contratar | CDC art. 49: 7 dias para contratação a distância | **100%** se cancelar em até 24h e faltarem mais de 7 dias para o evento |
| Comprovante | Muitas vezes só conversa de mensagem | **Comprovante com código de verificação** |

## Pontos para o grupo discutir

1. **Prazo de arrependimento:** o ArtConnect dá 24 horas, mas o CDC fala em **7 dias** para contratação pela internet. Vale rever a política para seguir o art. 49 e evitar problema com cliente ou Procon.
2. **Caso fortuito:** a política não fala do que acontece quando o evento não pode acontecer por motivo que ninguém controla (chuva forte, interdição, doença). Seguindo o TJ-SP, o certo seria devolver sem multa ou remarcar a data.
3. **Remarcação:** oferecer “remarcar a data” antes de cancelar é uma prática que agrada cliente e artista.

## Fontes

- Código Civil, art. 408 e 417 a 420: https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm
- Código de Defesa do Consumidor, art. 49 e 51: https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm
- OAB-RS, “Contrato por WhatsApp segue regra de arrependimento do CDC”: https://www2.oabrs.org.br/jornalDaOrdem/contrato-por-whatsapp-segue-regra-de-arrependimento-do-codigo-de-defesa-do-consumidor/49268
- Conjur, “Buffet não pode cobrar multa por festa cancelada pela covid-19” (TJ-SP, 2021): https://www.conjur.com.br/2021-mar-31/buffet-nao-cobrar-multa-festa-cancelada-covid-19/
- Política de cancelamento do ArtConnect: `Documentos/Sprint 6/politica-cancelamento-reembolso.md` e `artconnect-django/ArtConnect/politicas.py`
