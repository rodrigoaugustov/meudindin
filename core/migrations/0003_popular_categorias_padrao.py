# Em core/migrations/000X_popular_categorias_padrao.py

from django.db import migrations

CATEGORIAS_PADRAO = [
    "Alimentação", "Moradia", "Transporte", "Saúde", "Lazer", 
    "Educação", "Compras", "Serviços", "Impostos e Taxas",
    "Salário", "Renda Extra", "Investimentos"
]

def criar_categorias(apps, schema_editor):
    """
    Cria as categorias padrão do sistema (com usuario=None).
    """
    Categoria = apps.get_model('core', 'Categoria')
    for nome_categoria in CATEGORIAS_PADRAO:
        # O `get_or_create` garante que não vamos criar duplicatas se a migração rodar mais de uma vez
        Categoria.objects.get_or_create(nome=nome_categoria, usuario=None)

def remover_categorias(apps, schema_editor):
    """
    (Opcional, mas boa prática) Remove as categorias se a migração for revertida.
    """
    Categoria = apps.get_model('core', 'Categoria')
    Categoria.objects.filter(usuario__isnull=True, nome__in=CATEGORIAS_PADRAO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_categoria_usuario'),  # O nome da sua migração anterior
    ]

    operations = [
        migrations.RunPython(criar_categorias, reverse_code=remover_categorias),
    ]