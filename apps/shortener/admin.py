from django.contrib import admin

from .views import shorten_url
from .models import ShortUrl

class ShortUrlAdmin(admin.ModelAdmin):
    search_fields = ('short_url', 'long_url')
    list_display = ("short_url", "count", "long_url")
    readonly_fields = ("short_url", "count")

    def save_model(self, request, obj, form, change):
        obj.short_url = shorten_url(obj.long_url)

admin.site.register(ShortUrl, ShortUrlAdmin)
