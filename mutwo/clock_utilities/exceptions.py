__all__ = ("UndefinedConverterForTagWarning", "BadStaffCountWarning")


class UndefinedConverterForTagWarning(Warning):
    def __init__(self, undefined_tag: str):
        super().__init__(
            f"No converter has been defined for tag = '{undefined_tag}'. Events are ignored."
        )


class BadStaffCountWarning(Warning):
    def __init__(self, staff_count: int, expected_staff_count: int, tag: str):
        super().__init__(
            f"When converting event with tag '{tag}' the resulting "
            f"staff group had a {staff_count} staves, but the converter "
            f"expected {expected_staff_count} staves. This leads to bad "
            "looking notation, please use the same sequential event count in "
            "each event placement!"
        )
