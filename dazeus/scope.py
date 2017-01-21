class Scope:
    def __init__(self, network = None, receiver = None, sender = None):
        self.network = network
        self.receiver = receiver
        self.sender = sender

    def is_all(self):
        return self.network is None and self.receiver is None and self.sender is None

    def to_list(self):
        scope = []

        if self.network is not None:
            scope.append(self.network)
            if self.receiver is not None:
                scope.append(self.receiver)
                if self.sender is not None:
                    scope.append(self.sender)

        return scope

    def to_command_list(self):
        if self.receiver is not None and self.sender is not None:
            raise RuntimeError("Cannot use scope with both sender and receiver for subscribing to commands")

        scope = []
        if self.network is not None:
            scope.append(self.network)

            if self.receiver is not None:
                scope.append(False)
                scope.append(self.receiver)

            if self.sender is not None:
                scope.append(True)
                scope.append(self.sender)
        return scope
