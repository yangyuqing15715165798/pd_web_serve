from django.db import models


class pd(models.Model):
    id = models.AutoField(primary_key=True)
    sample_info_id = models.IntegerField()
    max_peak = models.FloatField()
    phase = models.FloatField()
    freq = models.FloatField()
    tim = models.FloatField()
    waveform = models.BinaryField()
    data_time = models.TimeField()

    class Meta:
        db_table = "sample_data"


class dynamic_routes(models.Model):
    id = models.CharField(max_length=20, primary_key=True)
    path = models.CharField(max_length=20)
    component = models.CharField(max_length=30)
    children_path = models.CharField(max_length=30)
    children_component = models.CharField(max_length=255)
    children_name = models.CharField(max_length=30)
    children_meta_title = models.CharField(max_length=30)
    children_meta_icon = models.CharField(max_length=30)

    class Meta:
        db_table = "dynamic_routes"

class user_login(models.Model):
    username = models.CharField(max_length=255, primary_key=True)
    password = models.CharField(max_length=255)

    class Meta:
        db_table = "user_info"

