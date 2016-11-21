from django.contrib import admin

from .models import Device, DeviceChallengeToken

class InlineDeviceChallengeTokenAdmin(admin.TabularInline):
    model = DeviceChallengeToken
    extra = 0

class DeviceChallengeTokenAdmin(admin.ModelAdmin):
    search_fields = ('device__user__username',)
    list_display = ('device_user', 'device', 'token', 'is_used',)
    list_editable = ('is_used',)
    
    def device_user(self, obj):
        return obj.device.user
    

class DeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_id',)
    inlines = [InlineDeviceChallengeTokenAdmin,]

admin.site.register(Device, DeviceAdmin)
admin.site.register(DeviceChallengeToken, DeviceChallengeTokenAdmin)
