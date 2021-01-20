import argparse


def unsigned_int_validator(arg):
    try:
        i = int(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("The argument must be an integer")
    if i < 0:
        raise argparse.ArgumentTypeError(f"The argument must be > {0}")
    return i


def logmode_validator(arg):
    if arg in ['ALL', 'ERROR', 'WARNING', 'DISABLE']:
        return arg
    raise argparse.ArgumentTypeError("Unknown mode")
