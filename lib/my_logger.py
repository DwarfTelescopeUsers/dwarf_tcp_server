import config


def debug(*messages):
    if config.DEBUG:
        for message in messages:
            print(message)


def error(*messages):
    for message in messages:
        print(message)
