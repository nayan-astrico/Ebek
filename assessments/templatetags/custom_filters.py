from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value."""
    return value - arg

@register.filter
def add(value, arg):
    """Add the arg from the value."""
    return value + arg

@register.filter
def range_filter(value):
    """Custom range filter."""
    return range(1, value + 1)