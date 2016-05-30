# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-05-30 00:12
from __future__ import unicode_literals

import assessment.validator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0003_auto_20160527_0909'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assessment',
            name='rank',
        ),
        migrations.AlterField(
            model_name='assessment',
            name='point',
            field=models.IntegerField(validators=[assessment.validator.validate_point]),
        ),
    ]