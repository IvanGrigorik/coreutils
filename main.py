'''
This filed used to analyze options from source files
'''

from pathlib import Path

FILEDIR = Path(__file__).parent
SRCDIR = FILEDIR / "src"


class Command:
    name: str
    short_opts: list[str]
    long_opts: list[str]

    file_content: list[str]
    file_path: str

    def __init__(self):
        pass

    def __init__(self, name: str, path: str):
        self.name = name
        self.file_path = path
        self.long_opts = []

        with open(path, 'r') as f:
            self.file_content = [x.removesuffix('\n') for x in f.readlines()]


def main():

    # Load content of all source files from the src dir
    commands: list[Command] = []
    for file in SRCDIR.iterdir():
        # Skip all non-src files
        if not file.name.endswith(".c"):
            continue
        commands.append(Command(file.name.removesuffix(".c"), file.absolute()))

    # Parse short options
    for command in commands:
        # Get long options:
        # no long opt structure - skip file (TODO: change later (?))

        l_longopt = "long_options[]"
        s_longopt = "longopts[]"
        opt_suffix: tuple = (
            l_longopt, l_longopt + " =", l_longopt + " = {", s_longopt + " =", s_longopt + " = {")

        if not any(s.endswith(opt_suffix) for s in command.file_content):
            continue

        # Get start and end of the opt section
        startIdx = next((command.file_content.index(
            s) + 2 for s in command.file_content if s.endswith(opt_suffix)), None)

        endIdx = next((command.file_content[startIdx:].index(s) + startIdx
                      for s in command.file_content[startIdx:] if s.endswith("};")), None)

        long_options = command.file_content[startIdx:endIdx]
        # Parse long options

        for str in long_options:
            words = str.strip().lstrip("{").rstrip("},").split(" ")
            if len(words) >= 0 and words[0].startswith("\""):
                command.long_opts.append(words[0].strip('\"'))
            elif len(words) >= 0 and words[0] == "GETOPT_HELP_OPTION_DECL":
                command.long_opts.append("help")
            elif len(words) >= 0 and words[0] == "GETOPT_VERSION_OPTION_DECL":
                command.long_opts.append("version")
            elif len(words) >= 0 and words[0] == "GETOPT_SELINUX_CONTEXT_OPTION_DECL":
                command.long_opts.append("context")





if __name__ == "__main__":
    main()
