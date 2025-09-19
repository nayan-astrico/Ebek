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

@register.filter
def check_icon_navigation_permissions(user, tab_name):
    """Check if user has navigation permission for a specific tab."""
    if hasattr(user, 'check_icon_navigation_permissions'):
        return user.check_icon_navigation_permissions(tab_name)
    return False