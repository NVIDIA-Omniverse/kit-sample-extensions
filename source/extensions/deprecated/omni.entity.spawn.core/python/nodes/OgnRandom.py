import random


class OgnRandom:
    def compute(db):
        db.outputs.value = random.random()
        return True
