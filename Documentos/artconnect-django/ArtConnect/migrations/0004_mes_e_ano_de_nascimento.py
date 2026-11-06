from django.db import migrations, models


class Migration(migrations.Migration):
    """A idade deixa de ser digitada: a conta guarda o mês e o ano de nascimento e a idade é calculada."""

    dependencies = [
        ("ArtConnect", "0003_estado_e_idade"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="perfil",
            name="idade",
        ),
        migrations.AddField(
            model_name="perfil",
            name="ano_nascimento",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="perfil",
            name="mes_nascimento",
            field=models.PositiveSmallIntegerField(
                blank=True,
                choices=[
                    (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"), (4, "Abril"), (5, "Maio"), (6, "Junho"),
                    (7, "Julho"), (8, "Agosto"), (9, "Setembro"), (10, "Outubro"), (11, "Novembro"), (12, "Dezembro"),
                ],
                null=True,
            ),
        ),
    ]
