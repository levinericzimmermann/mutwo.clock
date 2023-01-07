__all__ = ("UndefinedConverterForTagWarning",)


class UndefinedConverterForTagWarning(Warning):
    def __init__(self, undefined_tag: str):
        super().__init__(
            f"No converter has been defined for tag = '{undefined_tag}'. Events are ignored."
        )
