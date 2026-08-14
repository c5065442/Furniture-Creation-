# flight.py
from datetime import datetime
from util import format_date

class Flight:
    def __init__(self, flight_no, from_, to, departure_time, arrival_time):
        self.flight_no = flight_no
        self.from_ = from_
        self.to = to
        self.departure_time = departure_time
        self.arrival_time = arrival_time

    def display_details(self):
        print(f"Flight {self.flight_no}: {self.from_} → {self.to}")
        print(f"  Departure: {format_date(self.departure_time)}")
        print(f"  Arrival:   {format_date(self.arrival_time)}")