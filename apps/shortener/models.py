from django.db import models

class ShortUrl(models.Model):
    short_url = models.CharField(max_length = 32,unique=True)
    long_url = models.CharField(max_length = 1024)
    count = models.IntegerField(default=0)
    class Meta:
        index_together = (('short_url',),)
