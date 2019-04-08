# Generated by Django 2.1.7 on 2019-04-08 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djangosnapshotpublisher', '0005_releasedocument_deleted'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReleaseDocumentExtraParameter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(max_length=255)),
                ('content', models.TextField(null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='contentreleaseextraparameter',
            name='content_release',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='djangosnapshotpublisher.ContentRelease'),
        ),
        migrations.AlterField(
            model_name='releasedocument',
            name='content_type',
            field=models.CharField(default='content', max_length=100),
        ),
        migrations.AlterField(
            model_name='releasedocument',
            name='document_key',
            field=models.CharField(max_length=250),
        ),
        migrations.AddField(
            model_name='releasedocumentextraparameter',
            name='release_document',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='djangosnapshotpublisher.ReleaseDocument'),
        ),
    ]
