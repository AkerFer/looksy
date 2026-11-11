from django.db import migrations


def add_categories(apps, schema_editor):
    category = apps.get_model('wardrobe', 'ClothingCategory')
    for name, slot in [('Худи', 'top'), ('Джинсы', 'bottom'), ('Другие вещи', 'other')]:
        category.objects.using(schema_editor.connection.alias).get_or_create(name=name, defaults={'slot': slot})


class Migration(migrations.Migration):
    dependencies = [('wardrobe', '0003_clothingitem_brand_clothingitem_fit_and_more')]
    operations = [migrations.RunPython(add_categories, migrations.RunPython.noop)]
