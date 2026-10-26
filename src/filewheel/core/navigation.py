"""Capability-derived destinations, shared by preview and installed registries."""

ORDER = ('Image', 'Document', 'To MD', 'Markdown/Text', 'Audio', 'Video')


def destination(capability, source):
    if source.suffix.lower() == '.md':
        return 'From MD'
    if capability.output_extension.lower() == '.md':
        return 'To MD'
    return capability.category


def formats(capabilities, source, category):
    return tuple(c for c in capabilities if c.input_extension.lower() == source.suffix.lower()
                 and destination(c, source) == category)


def categories(capabilities, source):
    offered = {destination(c, source) for c in capabilities
               if c.input_extension.lower() == source.suffix.lower()}
    return ('From MD',) if 'From MD' in offered else tuple(c for c in ORDER if c in offered)
