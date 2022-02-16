import random
import string


def get_random_alphanumeric(length: int) -> str:
    ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))