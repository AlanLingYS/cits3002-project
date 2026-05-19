# This is where simulation starts

# Should do:
# create Host A, Router, Host B
# call send function
# print start/end logs

import sys
from device import NetworkSimulator

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

def main(argv=None):
    """Run the fixed Host A to Host B simulation."""

    args = sys.argv if argv is None else argv
    try:
        message_size = parse_message_size(args)
    except ValueError as exc:
        print(exc)
        return 1

    simulator = NetworkSimulator()
    simulator.send_from_a_to_b(message_size)
    return 0
