# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-20 09:19
from django.db import migrations, models


def forwards_func(apps, schema_editor):
    Worker = apps.get_model("lava_scheduler_app", "Worker")

    for worker in Worker.objects.all():
        if not worker.display:
            worker.health = 2
            worker.save()


def backwards_func(apps, schema_editor):
    Worker = apps.get_model("lava_scheduler_app", "Worker")

    for worker in Worker.objects.all():
        if worker.health in [1, 2]:
            worker.display = False
        else:
            worker.display = True
        worker.save()


class Migration(migrations.Migration):

    dependencies = [("lava_scheduler_app", "0030_unused_scheduler_fields")]

    operations = [
        migrations.AddField(
            model_name="worker",
            name="health",
            field=models.IntegerField(
                choices=[(0, "Active"), (1, "Maintenance"), (2, "Retired")], default=0
            ),
        ),
        migrations.AddField(
            model_name="worker",
            name="state",
            field=models.IntegerField(
                choices=[(0, "Online"), (1, "Offline")], default=1, editable=False
            ),
        ),
        migrations.RunPython(forwards_func, backwards_func, elidable=True),
        migrations.RemoveField(model_name="worker", name="display"),
    ]
