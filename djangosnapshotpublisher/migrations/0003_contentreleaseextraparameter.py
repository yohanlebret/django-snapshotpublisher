# Generated by Django 2.1.7 on 2019-03-11 10:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djangosnapshotpublisher', '0002_auto_20190311_0937'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReleaseExtraParameter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(max_length=100)),
                ('content', models.TextField(null=True)),
                ('content_release', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='djangosnapshotpublisher.ContentRelease')),
            ],
        ),
    ]
