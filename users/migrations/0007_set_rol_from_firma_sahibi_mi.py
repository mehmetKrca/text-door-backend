from django.db import migrations


def rol_ata(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    CustomUser.objects.filter(firma_sahibi_mi=True).update(rol='patron')
    CustomUser.objects.filter(firma_sahibi_mi=False).update(rol='usta')


def rol_geri_al(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    CustomUser.objects.all().update(rol='usta')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_add_customuser_rol'),
    ]

    operations = [
        migrations.RunPython(rol_ata, rol_geri_al),
    ]
