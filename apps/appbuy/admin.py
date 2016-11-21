# -*- coding: utf-8 -*-

from django.contrib import admin
from .models import BoughtApp, BlackList, AccountBalance
from .views import capp

def resend_order(modeladmin, request, queryset):
    for q in queryset:
        args = [str(i) for i in [q.id, q.itunes_id, q.user.id, q.apple_id]]
        capp.send_task('apple.tasks.gift_app', args=args)

resend_order.short_description = "ارسال مجدد سفارش"

class BoughtAppAdmin(admin.ModelAdmin):
    list_display = ('user', 'app_name', 'itunes_id', 'ir_fee', 'us_fee', 'buy_date', 'status')
    search_fields = ('user__username', 'app_name', 'itunes_id')
    list_filter = ('status',)
    ordering = ('-buy_date',)
    actions = [resend_order]

class BlackListAdmin(admin.ModelAdmin):
    list_display = ('itunes_id', 'date')
    search_field = ('itunes_id', 'description')

admin.site.register(BoughtApp, BoughtAppAdmin)
admin.site.register(BlackList, BlackListAdmin)
admin.site.register(AccountBalance)
