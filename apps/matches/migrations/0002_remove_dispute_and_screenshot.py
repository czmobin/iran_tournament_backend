# Generated manually for cleanup of Match and Game models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('matches', '0001_initial'),
    ]

    operations = [
        # Remove screenshot field from Game model
        migrations.RemoveField(
            model_name='game',
            name='screenshot',
        ),

        # Delete MatchDispute model entirely
        migrations.DeleteModel(
            name='MatchDispute',
        ),
    ]
