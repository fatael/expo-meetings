from django import template

from ..i18n import DEFAULT_LANGUAGE, tr

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, text):
    """{% t "English phrase" %} – the phrase in the current language."""
    return tr(context.get("lang", DEFAULT_LANGUAGE), text)


@register.filter
def trans(text, lang):
    """{{ value|trans:lang }} – translate a variable."""
    return tr(lang, str(text))


@register.filter
def ltr(text):
    """Keep times and dates in left-to-right order inside right-to-left text."""
    return f"\u2066{text}\u2069"
