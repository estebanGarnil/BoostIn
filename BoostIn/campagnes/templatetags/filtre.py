from django import template

register = template.Library()

@register.filter
def remove_first(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8')  # Decode from bytes to string
    return value if value else ''
