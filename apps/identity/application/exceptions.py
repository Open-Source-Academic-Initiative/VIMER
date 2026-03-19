class RegistrationError(Exception):
    pass


class DuplicateTaxIdError(RegistrationError):
    pass


class DuplicateUsernameError(RegistrationError):
    pass


class DuplicateEmailError(RegistrationError):
    pass


class RegistrationValidationError(RegistrationError):
    def __init__(self, messages=None, message_dict=None):
        self.message_dict = {
            field: list(dict.fromkeys(field_messages))
            for field, field_messages in (message_dict or {}).items()
        }
        collected_messages = list(messages or [])
        for field_messages in self.message_dict.values():
            collected_messages.extend(field_messages)
        self.messages = list(dict.fromkeys(collected_messages))
        super().__init__(" ".join(self.messages))
