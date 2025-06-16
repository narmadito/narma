from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailVerificationCode, Block

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('username', 'email', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    ordering = ('username',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile', {'fields': ('profile_picture',)}),
    )

@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'new_email', 'new_email_code_created_at')
    search_fields = ('user__username', 'user__email', 'code', 'new_email')
    readonly_fields = ('created_at', 'new_email_code_created_at')

@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
    search_fields = ('blocker__username', 'blocked__username')
