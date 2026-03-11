class RegistrationError(Exception):
    pass


class DuplicateTaxIdError(RegistrationError):
    pass
