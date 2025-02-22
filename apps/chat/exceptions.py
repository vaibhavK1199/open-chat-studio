class ChatException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class AudioSynthesizeException(ChatException):
    def __init__(self, message):
        super().__init__(message)


class AudioTranscriptionException(ChatException):
    def __init__(self, message):
        super().__init__(message)


class ChannelException(ChatException):
    def __init__(self, message):
        super().__init__(message)


class ParticipantNotAllowedException(Exception):
    pass


class VersionedExperimentSessionsNotAllowedException(ChatException):
    pass
