# This is where simulation starts

# Should do:
# create Host A, Router, Host B
# call send function
# print start/end logs

import sys

def parse_message_size(argv):
#validate the required message-size argument

    if len(argv) != 2:
        raise ValueError("usage: python main.py <message_size_bytes>")

    try:
        message_size = int(argv[1])
    except ValueError as exc:
        raise ValueError("message_size_bytes must be an integer") from exc

    if message_size < 0:
        raise ValueError("message_size_bytes must be non-negative")

    return message_size