# Generated by Django 2.1.5 on 2019-01-26 18:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("homevisit", "0006_meeting_group")]

    operations = [
        migrations.AlterField(
            model_name="meeting",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="homevisit.MeetingGroup"
            ),
        )
    ]
