from datetime import date

from django.db import migrations, models


def copiar_mes_e_ano(apps, schema_editor):
    """Contas que já tinham mês e ano ficam com o dia 1 desse mês (dá para corrigir em Editar perfil)."""
    Perfil = apps.get_model("ArtConnect", "Perfil")
    for perfil in Perfil.objects.exclude(ano_nascimento=None).exclude(mes_nascimento=None):
        perfil.data_nascimento = date(perfil.ano_nascimento, perfil.mes_nascimento, 1)
        perfil.save(update_fields=["data_nascimento"])


class Migration(migrations.Migration):
    """A conta passa a guardar a data de nascimento completa (dia, mês e ano)."""

    dependencies = [
        ("ArtConnect", "0004_mes_e_ano_de_nascimento"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="data_nascimento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(copiar_mes_e_ano, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="perfil",
            name="ano_nascimento",
        ),
        migrations.RemoveField(
            model_name="perfil",
            name="mes_nascimento",
        ),
    ]
