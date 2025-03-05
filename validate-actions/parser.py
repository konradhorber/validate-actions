import yaml


class Token:
    def __init__(self, line_no, curr, prev, next, nextnext):
        self.line_no = line_no
        self.curr = curr
        self.prev = prev
        self.next = next
        self.nextnext = nextnext


def tokenize(buffer):
    yaml_loader = yaml.BaseLoader(buffer)

    try:
        prev = None
        curr = yaml_loader.get_token()
        while curr is not None:
            next = yaml_loader.get_token()
            nextnext = (yaml_loader.peek_token()
                        if yaml_loader.check_token() else None)

            yield Token(curr.start_mark.line + 1, curr, prev, next, nextnext)

            prev = curr
            curr = next

    except yaml.scanner.ScannerError:
        pass