class OwnershipInconsistency(Exception):
    """
    Raised when the design-wizard views detect an inconsistency with regard to object-ownership Examples:

    * User1 is trying to use Body b1 to make a pattern, but b1.user is User2.
    * User1 is trying to use Swatch s1 to make a pattern, but s1.user is User2.

    We do not use this when user U1 is trying to directly access an object that belongs to another (e.g., User1 is
    trying to tweak an IGP that belongs to User2). In those cases, we raise PermissionDenied. This exception is only for
    when the inconsistency occurs further down-- User1 is trying to make/tweak an IGP that belongs to them but uses
    a Body that belongs to another user.

    Also, we don't use this exception when the inconsistency occurs at the customer-linkage level. For those, we use
    CustomerInconsistency.
    """

    pass
