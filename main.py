'''
This filed used to analyze options from source files
'''

from pathlib import Path
import re

FILEDIR = Path(__file__).parent
SRCDIR = FILEDIR / "src"


class ShortOption:
    name: str
    # www.gnu.org/software/libc/manual/html_node/Using-Getopt.html
    is_noarg: bool              # X
    is_required: bool           # X:
    is_optional: bool           # X::
    is_posix_compliant: bool    # +X (for each option in the shortopt list)
    is_non_opts: bool           # -X (for each option in the shortopt list)

    def __init__(self, name: str = "",
                 is_noarg: bool = False,
                 is_required: bool = False,
                 is_optional: bool = False,
                 is_posix_compliant: bool = False,
                 is_non_opts: bool = False):
        self.name = name
        self.is_noarg = is_noarg
        self.is_required = is_required
        self.is_optional = is_optional
        self.is_posix_compliant = is_posix_compliant
        self.is_non_opts = is_non_opts

        # Check for valid options
        if (is_noarg and is_required or
            is_required and is_optional or
                is_noarg and is_optional or
                is_posix_compliant and is_non_opts):
            raise Exception("Invalid options")


class Command:
    name: str
    short_opts: list[ShortOption]
    long_opts: list[str]

    file_content: list[str]
    file_path: str

    def __init__(self):
        self.long_opts = []
        self.short_opts = []
        self.file_content = []

    def __init__(self, name: str, path: str):
        self.name = name
        self.file_path = path
        self.long_opts = []
        self.short_opts = []

        with open(path, 'r') as f:
            self.file_content = [x.removesuffix('\n') for x in f.readlines()]


def parse_short_opt(opts: list[str]) -> list[ShortOption]:
    # Parse list of options:
    ret_opts: list[ShortOption] = []
    is_posix_compliant: bool
    is_non_opts: bool

    if len(opts) > 1:
        is_posix_compliant: bool = False
        is_non_opts: bool = False

    # Divide all options
    divided_opts: list[str] = []
    for opt in opts:
        if opt[0] == '+':
            is_posix_compliant = True
        elif opt[0] == '-':
            is_non_opts = True

        # Parse each option
        if opt[0] == '+' or opt[0] == '-':
            opt = opt[1:]

        op_divided = re.findall(r'[A-Za-z0-9]:{0,2}', opt)
        divided_opts.extend(op_divided)

    # Parse all options
    for opt in divided_opts:
        ret_opt = ShortOption()
        ret_opt.name = opt.strip(":")
        if opt.endswith("::"):
            ret_opt.is_optional = True
        elif opt.endswith(':'):
            ret_opt.is_required = True
        else:
            ret_opt.is_noarg = True
        ret_opt.is_posix_compliant = is_posix_compliant
        ret_opt.is_non_opts = is_non_opts
        ret_opts.append(ret_opt)

    return ret_opts


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
        # Long options:
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

        endIdx = next((i + startIdx
                      for i, s in enumerate(command.file_content[startIdx:]) if s.endswith("};")), None)

        long_options = command.file_content[startIdx:endIdx]

        # Parse long options
        for opt in long_options:
            words = opt.strip().lstrip("{").rstrip("},").split(" ")
            if len(words) >= 0 and words[0].startswith("\""):
                command.long_opts.append(words[0].strip('\"'))
            elif len(words) >= 0 and words[0] == "GETOPT_HELP_OPTION_DECL":
                command.long_opts.append("help")
            elif len(words) >= 0 and words[0] == "GETOPT_VERSION_OPTION_DECL":
                command.long_opts.append("version")
            elif len(words) >= 0 and words[0] == "GETOPT_SELINUX_CONTEXT_OPTION_DECL":
                command.long_opts.append("context")

        # Short options
        # Parse the short options from the variable
        if any(s.endswith("short_options[] =") for s in command.file_content):
            # Get short option var position
            startIdx = next((i for i, s in enumerate(command.file_content)
                             if "short_options[]" in s), -1)
            if startIdx < 0:
                raise ("Unknown short options!")
            endIdx = next((i + startIdx + 1 for i, s in enumerate(
                command.file_content[startIdx:]) if s.endswith(";")), None)

            short_options = command.file_content[startIdx:endIdx]

            options: list[str] = []
            for opt in short_options:
                startIdx = opt.find("\"")
                endIdx = opt.rfind("\"")
                if startIdx < 0 or endIdx < 0:
                    continue
                options.append(opt[startIdx:endIdx+1].strip("\""))

            command.short_opts.append(parse_short_opt(options))

        else:
            # Else - get short option from the getopt_long
            pass


if __name__ == "__main__":
    main()
