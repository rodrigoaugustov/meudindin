# core/templatetags/widget_tweaks.py
from django import template

register = template.Library()

@register.filter(name='attr')
def attr(field, attrs_str):
    attrs = {}
    for pair in attrs_str.split(','):
        if ':' in pair:
            key, value = pair.split(':', 1)
            attrs[key.strip()] = value.strip()
    
    return field.as_widget(attrs=attrs)