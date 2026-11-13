# Estudo de caso: GigSalad e The Bash, plataformas de contratação que deram certo

**Sprint 9 · Tarefa difícil**

Nos Estados Unidos já existem plataformas que fazem o que o ArtConnect propõe: conectar quem organiza uma festa a artistas e fornecedores. Este estudo analisa duas das mais conhecidas, **GigSalad** e **The Bash** (antiga GigMasters), para entender como elas funcionam e o que dá confiança a clientes e artistas.

## Como cada uma funciona

| Etapa | GigSalad | The Bash |
|---|---|---|
| **Encontrar** | O cliente busca e vê perfis, ou preenche um pedido rápido e a plataforma manda para os perfis mais adequados da região | O cliente busca por tipo de artista ou fornecedor e cidade |
| **Orçamento** | Os artistas recebem o pedido e mandam orçamento ou mensagem | Os fornecedores mandam orçamento, que chega por e-mail e na conta do cliente |
| **Conversa** | Mensagens pela plataforma ou por telefone, mas **a contratação tem que ser fechada na plataforma** | Mensagens pela plataforma; pagar por fora tira a proteção |
| **Contratar e pagar** | O cliente coloca os dados de pagamento e fecha a contratação no site | Botão “Book Now” ao lado do orçamento; o pagamento é processado pela Stripe |
| **Garantia** | “Worry-Free Guarantee”: proteção do pagamento para contratações fechadas no site | “Booking Guarantee”: reembolso de 100% de sinais e pagamentos feitos no site, ajuda para achar substituto se o fornecedor cancelar |
| **Avaliações** | Selo “Top Performer” para quem é bem avaliado, responde rápido e fecha contratos | Só quem contratou pode avaliar; a plataforma diz que **não remove nem edita** avaliações |
| **Suporte** | Página de contato para problemas graves | Especialistas por e-mail e telefone, inclusive para trocar fornecedor de última hora |
| **Antes do evento** | — | Checklist enviado **7 dias antes** do evento |

## O que as duas têm em comum

1. **Fechar e pagar dentro da plataforma.** A proteção só vale para o que é pago no site. É assim que elas ganham dinheiro e garantem a segurança.
2. **Garantia de dinheiro de volta.** Se o artista não aparece ou cancela, o cliente recebe de volta.
3. **Avaliações só de quem contratou.** Isso torna as avaliações confiáveis.
4. **Selo para os melhores.** Premiar quem responde rápido e é bem avaliado incentiva bom comportamento.
5. **Ajuda para substituir quem cancela.** O pior medo do cliente é ficar sem atração no dia.

Um ponto de atenção: a GigSalad diz que **não verifica** os fornecedores listados e recomenda que o cliente pesquise por conta própria.

## Comparação com o ArtConnect

| Recurso | GigSalad / The Bash | ArtConnect hoje |
|---|---|---|
| Pedido de orçamento enviado a vários artistas | Sim | Sim |
| Contratação e pagamento no site | Sim | Sim |
| Dinheiro protegido até o evento | Sim (garantia) | Sim (pagamento retido até o cliente confirmar) |
| Avaliação só de quem contratou | Sim | Sim |
| Selos para os melhores | Sim (Top Performer) | Sim (5 selos, ex.: Responde rápido) |
| Lembrete antes do evento | Sim (checklist de 7 dias, The Bash) | Sim (lembretes de 7 dias e da véspera) |
| Ajuda para achar substituto se o artista cancelar | Sim | **Ainda não** |
| Ordenação por compatibilidade com o evento | Não destacada | **Sim (match)**, um diferencial |

## Lições para o ArtConnect

1. **Criar o “substituto automático”:** quando um artista cancela, sugerir na hora outros artistas compatíveis e livres na mesma data. É a lacuna mais clara em relação às duas plataformas.
2. **Dar nome à garantia:** o ArtConnect já protege o pagamento, mas não dá um nome a isso. Uma “Garantia ArtConnect” explicada numa página ajudaria a passar confiança.
3. **Deixar claro que pagar por fora tira a proteção:** avisar isso nas mensagens entre cliente e artista.
4. **Manter o match como diferencial:** nenhuma das duas destaca a compatibilidade com o evento do jeito que o ArtConnect faz.

## Fontes

- GigSalad, “How GigSalad works”: https://help.gigsalad.com/article/47-how-it-works
- GigSalad, “Why you should book gigs through GigSalad”: https://help.gigsalad.com/article/118-why-book-gigs-through-gigsalad
- The Bash, “Booking Guarantee”: https://www.thebash.com/guarantee
- The Bash, “GigMasters is now The Bash”: https://thebash.com/articles/gigmasters-the-bash
