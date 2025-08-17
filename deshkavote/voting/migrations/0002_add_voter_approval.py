# Generated migration for voter approval system
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0001_initial'),  # Your existing migration
    ]

    operations = [
        migrations.AddField(
            model_name='voter',
            name='approval_status',
            field=models.CharField(
                choices=[('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                default='pending',
                max_length=10
            ),
        ),
        migrations.AddField(
            model_name='voter',
            name='approved_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='approved_voters',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='voter',
            name='approval_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='voter',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='is_active',
            field=models.BooleanField(default=False),  # Changed default to False for approval workflow
        ),
        migrations.AddField(
            model_name='election',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]