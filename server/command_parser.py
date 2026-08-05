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

        parts = raw.strip().split(
            maxsplit=1
        )


        name=parts[0].upper()


        argument=""

        if len(parts)>1:
            argument=parts[1]


        return FTPCommand(
            name,
            argument
        )