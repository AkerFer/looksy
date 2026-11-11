from django.db import migrations

CATEGORIES = [('Футболки','top'),('Рубашки','top'),('Свитеры','top'),('Брюки','bottom'),('Юбки','bottom'),('Платья','dress'),('Верхняя одежда','outerwear'),('Обувь','shoes'),('Аксессуары','accessory')]
COLORS = [('Чёрный','#000000'),('Белый','#FFFFFF'),('Серый','#808080'),('Синий','#0000FF'),('Красный','#FF0000'),('Зелёный','#008000'),('Бежевый','#F5F5DC')]
def seed(apps,schema_editor):
    Category=apps.get_model('wardrobe','ClothingCategory')
    Color=apps.get_model('wardrobe','ClothingColor')
    for name,slot in CATEGORIES: Category.objects.get_or_create(name=name,defaults={'slot':slot})
    for name,code in COLORS: Color.objects.get_or_create(name=name,defaults={'hex_code':code})
class Migration(migrations.Migration):
    dependencies=[('wardrobe','0001_initial')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
