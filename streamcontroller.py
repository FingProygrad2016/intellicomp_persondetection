class StreamController:

    def __init__(self):
        self.streamings = {}

    def add(self, identifier, p):
        self.streamings[identifier] = p

    def remove(self, identifier):
        p = self.streamings.get(identifier)
        if p:
            self._terminate(p)
            del self.streamings[identifier]
        else:
            print("MASTER ERROR: Process was not fount in StreamControler.")

    def remove_all(self):
        for p in self.streamings.values():
            self._terminate(p)
        else:
            self.streamings = {}

    def get_identidiers(self):
        return self.streamings.keys()

    @staticmethod
    def _terminate(p):
        p.terminate()
        try:
            p.wait(2)
        except:
            p.kill()
