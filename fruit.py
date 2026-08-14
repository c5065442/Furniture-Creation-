# fruit.py
from datetime import datetime
from FlightManagementSystem.util import format_date

class Fruit:
    def __init__(self, name, sweetness, origin, harvest_date, best_before):
        self.name = name
        self.sweetness = sweetness
        self.origin = origin
        self.harvest_date = harvest_date
        self.best_before = best_before

    def __str__(self):
        harvest = format_date(self.harvest_date)
        best = format_date(self.best_before)
        return f"{self.name} from {self.origin} | Sweetness: {self.sweetness}/10 | Harvest: {harvest} | Best before: {best}"

    def add(self):
        with open("Fruit.txt", "a") as file:
            file.write(str(self) + "\n")

if __name__ == "__main__":
    fruit = Fruit("Apple", 8, "USA", 
                  datetime(2025, 6, 10, 8, 30),
                  datetime(2025, 6, 20, 23, 59))
    fruit.add()
    print(fruit)