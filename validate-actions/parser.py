import yaml

def tokenize(buffer):
    yaml_loader = yaml.BaseLoader(buffer)

    try:
        curr = yaml_loader.get_token()
        while curr is not None:
            next = yaml_loader.get_token()

            yield curr

            curr = next

    except yaml.scanner.ScannerError:
        pass