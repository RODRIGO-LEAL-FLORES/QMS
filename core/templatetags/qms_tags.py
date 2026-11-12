from urllib.parse import urlencode

from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def pagination_url(context, page_number):
    """Build a page URL while preserving active filters and searches."""
    request = context.get('request')
    if request is None:
        return f'?page={page_number}'

    query = request.GET.copy()
    query['page'] = page_number
    return f'?{urlencode(query, doseq=True)}'
