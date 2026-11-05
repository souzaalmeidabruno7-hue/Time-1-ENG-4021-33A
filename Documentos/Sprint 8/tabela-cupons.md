# Tabela de cupons de desconto

## Para que serve

Uma das estratégias para atrair os primeiros clientes é dar desconto na primeira contratação ou em campanhas (Dia das Mães, fim de ano). A tabela `cupons` guarda os códigos que o cliente digita na tela de pagamento. O desconto é **bancado pela plataforma**: o artista recebe o valor cheio do contrato.

## Criação (models.py, migração `0002_sprint8`)

```python
class Cupom(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPOS_CUPOM)          # percentual ou fixo
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    valor_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    desconto_maximo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    validade = models.DateField(null=True, blank=True)
    limite_usos = models.PositiveIntegerField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
```

A tabela `pagamentos` ganhou duas colunas: `cupom` (qual cupom foi usado) e `desconto` (quanto em reais).

## Colunas

| Coluna | Tipo | Regra |
|---|---|---|
| codigo | texto (20) | Único, sempre em maiúsculas. É o que o cliente digita |
| descricao | texto (120) | Explicação curta mostrada quando o cupom é aplicado |
| tipo | texto | `percentual` (10 = 10%) ou `fixo` (50 = R$ 50) |
| valor | decimal | Maior que zero. Se for percentual, no máximo 100 |
| valor_minimo | decimal | Valor mínimo do contrato para o cupom valer |
| desconto_maximo | decimal | Teto do desconto em reais (opcional) |
| validade | data | Último dia em que o cupom funciona (opcional) |
| limite_usos | inteiro | Quantas vezes o cupom pode ser usado no total (vazio = sem limite) |
| ativo | sim/não | Permite desligar um cupom sem apagar o histórico |

## Regras de uso

1. O cupom precisa estar **ativo** e **dentro da validade**.
2. O contrato precisa valer **pelo menos o valor mínimo** do cupom.
3. **Cada cliente usa cada cupom uma vez só.**
4. Se o cupom tiver **limite de usos**, ele para de funcionar quando o limite é atingido. Só contam os pagamentos confirmados.
5. **O desconto nunca passa de 50% do contrato**, mesmo se o cupom for maior. Isso protege a plataforma de erro de cadastro.
6. Se houver cancelamento, o reembolso é calculado sobre o valor que o cliente **pagou de fato**, com o desconto já descontado.

## Dados de exemplo

| Código | Tipo | Valor | Mínimo | Teto | Validade |
|---|---|---|---|---|---|
| BEMVINDO10 | percentual | 10% | R$ 500 | R$ 300 | 31/12/2027 |
| ARTE50 | fixo | R$ 50 | R$ 1.000 | — | 31/12/2027 |
| NATAL2025 | percentual | 15% | — | — | 31/12/2025 (vencido, para testar o erro) |

## Restrições no banco

- `codigo` é único (`UNIQUE`).
- `valor > 0` (`cupom_valor_positivo`).
- Cupom percentual com valor até 100 (`cupom_percentual_ate_100`).
- `pagamentos.cupom` usa `PROTECT`: um cupom já usado não pode ser apagado, só desativado.
