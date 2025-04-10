'''
This filed used to parse options from source files with `getopt_long` function
'''

from pathlib import Path
import re
import git
import yaml

FILE_DIR = Path(__file__).parent
REPOS_DIR = FILE_DIR / "repos"
COREUTILS_DIR = REPOS_DIR / "coreutils"
COREUTILS_SRC_DIR = COREUTILS_DIR / "src"
COREUTILS_REPO = "https://github.com/coreutils/coreutils.git"
OUT_FILE = FILE_DIR / "out.yaml"


class LongOption:
    name: str
    associated_char: str
    is_noarg: bool
    is_optional: bool
    is_required: bool

    def __init__(self, name: str = "",
                 associated_char="",
                 is_noarg: bool = False,
                 is_optional: bool = False,
                 is_required: bool = False,):
        self.name = name
        self.associated_char = associated_char
        self.is_noarg = is_noarg
        self.is_optional = is_optional
        self.is_required = is_required

    def get_arg_requirement(self) -> str:
        if not (self.is_noarg or self.is_optional or self.is_required):
            return "default"
        elif self.is_noarg:
            return "noarg"
        elif self.is_optional:
            return "optional"
        elif self.is_required:
            return "required"

    def __str__(self):
        return f"{self.name} : {self.associated_char}"

    def __repr__(self):
        return str(self)


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

    def get_arg_requirement(self) -> str:
        if not (self.is_noarg or self.is_required or self.is_optional):
            return "default"
        elif self.is_noarg:
            return "noarg"
        elif self.is_required:
            return "required"
        elif self.is_optional:
            return "optional"

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)


class Command:
    name: str
    short_opts: list[ShortOption]
    long_opts: list[LongOption]

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


def parse_shortopt_str(opts: list[str]) -> list[ShortOption]:
    if len(opts) < 2 and len(opts[0]) < 1:
        return []
    # Parse list of options:
    ret_opts: list[ShortOption] = []
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


def clone_repo():
    if ((COREUTILS_DIR).exists()):
        return
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from(COREUTILS_REPO, COREUTILS_DIR)


# returns: list of all command source files with loaded contents, names and paths
def parse_command_files() -> list[Command]:
    commands: list[Command] = []
    for file in COREUTILS_SRC_DIR.iterdir():
        # Skip all non-src files
        if not file.name.endswith(".c"):
            continue
        commands.append(Command(file.name.removesuffix(".c"), file.absolute()))

    return commands


def parse_longopts(command: Command) -> Command:
    l_longopt = "long_options[]"
    s_longopt = "longopts[]"
    ls_longopt = "long_opts[]"
    opt_suffix: tuple = (
        l_longopt, l_longopt + " =", l_longopt + " = {", s_longopt + " =", s_longopt + " = {", ls_longopt + " =")

    # Get start and end of the opt section
    start_idx = next((command.file_content.index(
        s) + 2 for s in command.file_content if s.endswith(opt_suffix)), None)

    end_idx = next((i + start_idx
                    for i, s in enumerate(command.file_content[start_idx:]) if s.endswith("};")), None)

    long_options = command.file_content[start_idx:end_idx]
    # Normalize string (if one option located in multiple strings. e.g. `{..., ...\n, ...}`, etc.)
    long_options = "".join(long_options)
    long_options = [opt.strip("}{, ") for opt in long_options.split("},")]

    # Parse long options
    for opt in long_options:
        words = opt.strip().lstrip("{").rstrip("},").split(", ")
        ret_opt: LongOption = LongOption()
        # Default long option
        if len(words) >= 0 and words[0].startswith("\""):
            ret_opt.name = words[0].strip('"')
            arg = words[1].strip(',')
            if arg == "no_argument" or arg == "0":
                ret_opt.is_noarg = True
            elif arg == "required_argument" or arg == "1":
                ret_opt.is_required = True
            elif arg == "optional_argument" or arg == "2":
                ret_opt.is_optional = True
            ret_opt.associated_char = words[3].strip("},'")
        elif len(words) >= 0 and words[0] == "GETOPT_HELP_OPTION_DECL":
            ret_opt.name = "help"
            ret_opt.associated_char = "GETOPT_HELP_CHAR"
            ret_opt.is_noarg = True
        elif len(words) >= 0 and words[0] == "GETOPT_VERSION_OPTION_DECL":
            ret_opt.name = "version"
            ret_opt.associated_char = "GETOPT_VERSION_CHAR"
            ret_opt.is_noarg = True
        elif len(words) >= 0 and words[0] == "GETOPT_SELINUX_CONTEXT_OPTION_DECL":
            ret_opt.name = "context"
            ret_opt.associated_char = "Z"
            ret_opt.is_optional = True
        else:
            continue
        command.long_opts.append(ret_opt)
    return command


def parse_shortopts_var(command: Command) -> Command:
    l_shortopt = "short_options[]"
    ls_shortopt = "short_opts ="
    s_shortopt = "shortopts[]"

    # Get short option var position
    start_idx = next((i for i, s in enumerate(command.file_content)
                      if l_shortopt in s or s_shortopt in s or ls_shortopt in s), -1)
    if start_idx < 0:
        raise ("Unknown short options!")
    end_idx = next((i + start_idx + 1 for i, s in enumerate(
        command.file_content[start_idx:]) if s.endswith(";")), None)

    short_options = command.file_content[start_idx:end_idx]

    options: list[str] = []
    for opt in short_options:
        start_idx = opt.find("\"")
        end_idx = opt.rfind("\"")
        if start_idx < 0 or end_idx < 0:
            continue
        options.append(opt[start_idx:end_idx+1].strip("\""))

    command.short_opts.extend(parse_shortopt_str(options))
    return command


# returns: getopt string start, getopt string end, getopt function index start and end
def get_getopt_indexes(command: Command, start_idx: int) -> tuple[int, int, int, int]:
    paren_start_idx = -1
    paren_end_idx = -1
    end_idx = -1
    getopt_idx = command.file_content[start_idx].index("getopt_long")

    paren_count = 0
    for i, _ in enumerate(command.file_content[start_idx:]):
        if paren_start_idx < 0:
            paren_start_idx = command.file_content[start_idx][getopt_idx:].index(
                "(") + getopt_idx
        if end_idx < 0 and ")" in command.file_content[start_idx + i] and paren_count == 0:
            end_idx = i + start_idx
            if i == 0:
                paren_end_idx = command.file_content[start_idx + i][paren_start_idx:].index(
                    ")") + paren_start_idx + 1
            else:
                paren_end_idx = command.file_content[start_idx + i].index(
                    ")") + paren_start_idx + 1
        if paren_start_idx > 0 and paren_end_idx > 0:
            break
        # Corner case - additional parenthesis in the getopt call (e.g. getopt(..., (), etc))
        if command.file_content[i + start_idx].count("(") > 0 and i > 0:
            paren_count += command.file_content[i +
                                                start_idx].count("(")
        if command.file_content[i + start_idx].count(")") > 0:
            paren_count -= command.file_content[i +
                                                start_idx].count(")")

    return (start_idx, end_idx, paren_start_idx, paren_end_idx)


def parse_shortopts(command: Command) -> Command:
    # Parse the short options from the variable
    l_shortopt = "short_options[]"
    ls_shortopt = "short_opts ="
    s_shortopt = "shortopts[]"
    if any(l_shortopt in s or s_shortopt in s or ls_shortopt in s for s in command.file_content):
        command = parse_shortopts_var(command)
        return command
    else:
        # Else - get short option from the getopt_long
        getopt_str = "getopt_long"
        start_idx = next((i for i, s in enumerate(
            command.file_content) if (getopt_str+" (" in s or getopt_str+"(" in s)), -1)

        # Initialize getopt indexes
        (start_idx,
         end_idx,
         paren_start_idx,
         paren_end_idx) = get_getopt_indexes(command, start_idx)

        getopt_call: str = ""
        # If getopt located on one line
        if end_idx == start_idx:
            getopt_call = command.file_content[start_idx][paren_start_idx:paren_end_idx]

        # Else - getopt is multi-line function call
        elif end_idx > start_idx:
            for i in range(start_idx, end_idx+1):
                if i == start_idx:
                    getopt_call += " " + \
                        command.file_content[i][paren_start_idx:].strip()
                elif i == end_idx:
                    getopt_call += " " + \
                        command.file_content[i][:paren_end_idx].strip()
                    break
                else:
                    getopt_call += " " + command.file_content[i].strip()
        else:
            raise Exception("Invalid getopt function parse")
        short_opt_pass = getopt_call.strip().split(", ")[2]
        options: list[str] = [x.strip("()\"")
                              for x in short_opt_pass.split(" ")]
        command.short_opts.extend(parse_shortopt_str(options))

    return command


def serialize_short_option(opt: ShortOption) -> dict:
    return {
        'name': opt.name,
        'option': opt.get_arg_requirement()
    }


def serialize_long_option(opt: LongOption) -> dict:
    return {
        'name': opt.name,
        'char': opt.associated_char,
        'option': opt.get_arg_requirement()
    }


def serialize_command(cmd: Command) -> dict:
    return {
        cmd.name: {
            'name': cmd.name,
            'is_posix_compliant': any(opt.is_posix_compliant for opt in cmd.short_opts),
            'is_non_opts': any(opt.is_non_opts for opt in cmd.short_opts),
            'shortopts': [serialize_short_option(opt) for opt in cmd.short_opts],
            'longopts': [serialize_long_option(opt) for opt in cmd.long_opts]
        }
    }


# dump list of commands into yaml file
def dump_yaml(commands: list[Command]):

    serialized = {}
    for cmd in commands:
        serialized.update(serialize_command(cmd))

    with open(OUT_FILE, 'w') as f:
        f.truncate()
        yaml.dump(serialized, f, sort_keys=False)


def main():
    # Clone coreutils repo
    clone_repo()

    commands: list[Command] = parse_command_files()

    # Parse short options
    for command in commands:
        # If no getopt_long - skip (TODO: change later (?))
        if not "getopt_long" in "".join(command.file_content):
            continue

        # Long options:
        command = parse_longopts(command)

        # Short options
        command = parse_shortopts(command)

    dump_yaml(commands)


if __name__ == "__main__":
    main()
