class FTPCommand:


    def __init__(
        self,
        name,
        argument=""
    ):
        self.name=name
        self.argument=argument



class CommandParser:

    @staticmethod
    def parse(raw):
        if not raw or not raw.strip():
            return FTPCommand("", "")

        parts = raw.strip().split(maxsplit=1)
        name = parts[0].upper()
        argument = parts[1] if len(parts) > 1 else ""

        return FTPCommand(name, argument)