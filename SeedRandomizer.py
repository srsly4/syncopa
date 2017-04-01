import random
import hashlib


def generate_seed():
    random.seed()
    rand_bytes = []
    for i in range(0, 16):
        rand_bytes.append(random.randint(0, 255))
    hash_gen = hashlib.sha1()
    hash_gen.update(bytes(rand_bytes))
    return hash_gen.hexdigest()[0:12]


def random_from_sorted_set(input_set : set):
    items = list(input_set)
    return random.choice(sorted(items))


def random_from_probability_list(sequence: list(dict())):
    if len(sequence) == 0:
        raise ValueError("Sequence can not be empty.")

    probability_grip = 0
    for item in sequence:
        probability_grip += item['probability']
        item['probability_range_end'] = probability_grip

    probability_sum = sum([item['probability'] for item in sequence])
    random_shot = random.random()*probability_sum

    for item in sequence:
        if item['probability_range_end'] > random_shot:
            return item
