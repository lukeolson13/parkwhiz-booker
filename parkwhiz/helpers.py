

FORMAT_MAPPER = {
    ' ': '%20',
    ',': '%2C',
    ':': '%3A',
}


def format_string(string):
    for char, replace_char in FORMAT_MAPPER.items():
        string = string.replace(char, replace_char)

    return string
