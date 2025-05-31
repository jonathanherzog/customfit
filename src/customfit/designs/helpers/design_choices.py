"""
In this module, we factor out constants (enums, really) which describe
aspects of a design. These are used all over the place, and so they
needed to be put in their own module to prevent circular imports among
the models which use them.
"""

# Visibility levels

PUBLIC = "PUBLIC"
LIMITED = "LIMITED"
PRIVATE = "PRIVATE"
FEATURED = "FEATURE"

VISIBILITY_CHOICES = (
    (FEATURED, "Featured"),
    (PUBLIC, "Viewable by all CF users"),
    (LIMITED, "Viewable by subscribers only"),
    (PRIVATE, "Not user visible"),
)


# Difficulty ratings
DESIGN_DIFFICULTY_CHOICES = [
    (1, "Very Easy"),
    (2, "Easy"),
    (3, "Intermediate"),
    (4, "Difficult"),
    (5, "Expert"),
]
