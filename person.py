# person.py
from datetime import datetime
from FlightManagementSystem.util import format_date

class Person:
    def __init__(self, firstname, lastname, dob, country, nationality, address):
        self.firstname = firstname
        self.lastname = lastname
        self.dob = dob          # datetime object
        self.country = country
        self.nationality = nationality
        self.address = address

    def __str__(self):
        dob_str = format_date(self.dob)
        return f"{self.firstname} {self.lastname} | Born: {dob_str} | {self.nationality} from {self.country} | {self.address}"

    def add(self):
        with open("Person.txt", "a") as file:
            file.write(str(self) + "\n")

if __name__ == "__main__":
    person = Person("Louise", "Wood", datetime(1990, 5, 15),
                    "Canada", "Canadian", "123 Maple St, Toronto")
    person.add()
    print(person)