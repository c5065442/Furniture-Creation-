# car.py
from datetime import datetime
from FlightManagementSystem.util import format_date

class Car:
    def __init__(self, make, model, model_year, speed):
        self.make = make
        self.model = model
        self.model_year = model_year  # datetime object
        self.speed = speed

    def __str__(self):
        formatted_year = format_date(self.model_year)
        return f"{self.make} {self.model} ({formatted_year}) - {self.speed} km/h"

    def add(self):
        """Append car details to Car.txt file."""
        with open("Car.txt", "a") as file:
            file.write(str(self) + "\n")

# Main execution block
if __name__ == "__main__":
    # Create a Car object with a datetime for model year
    car = Car("Toyota", "Camry", datetime(2024, 3, 1), 180)
    car.add()
    print(car)