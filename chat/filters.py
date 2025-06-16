import django_filters
from django.contrib.auth import get_user_model
from .models import GroupMessage
from .models import Group, DirectMessage

User = get_user_model()

class GroupMessageFilter(django_filters.FilterSet):
    sender = django_filters.ModelChoiceFilter(queryset=User.objects.none())

    class Meta:
        model = GroupMessage
        fields = ['sender']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        group = None
        if hasattr(self.request, 'parser_context'):
            group = self.request.parser_context.get('kwargs', {}).get('group_pk')
        if group:
            try:
                group_obj = Group.objects.get(pk=group)
                member_qs = group_obj.members.all()
                self.filters['sender'].queryset = member_qs
                self.filters['sender'].field.queryset = member_qs
            except Group.DoesNotExist:
                pass

