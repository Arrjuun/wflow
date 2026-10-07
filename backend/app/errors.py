class EngineError(Exception):
    def __init__(self, status: int, message):
        self.status = status
        self.message = message
        super().__init__(str(message))
