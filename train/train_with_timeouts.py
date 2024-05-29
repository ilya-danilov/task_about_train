from multiprocessing import Process, Event, Condition, BoundedSemaphore, Lock, synchronize
from multiprocessing import Value
from multiprocessing.sharedctypes import Synchronized
from time import sleep
from faker import Faker
from random import random


_WAIT_OPENING_STATION_COEFF = 8
_WAIT_TRAIN_COEFF = 30
_WAIT_OPENING_DOORS_AT_SOURCE_STATION_COEFF = 4
_WAIT_PASSENGERS_BOARDING_IS_OVER_COEFF = 8

operations = {
    '+': '__add__',
    '-': '__sub__'
}

class Passenger(Process):

    def __init__(
            self, name: int,
            opening_doors_at_source_station: synchronize.Event,
            train: synchronize.BoundedSemaphore,
            sending_train: synchronize.Event,
            controller: synchronize.Condition,
            passengers_boarding_is_over: synchronize.Event,
            opening_doors_at_another_station: synchronize.Event,
            passengers_quantity_on_train: Synchronized,
            passengers_quantity_on_train_lock: synchronize.Lock,
            opening_station: synchronize.Event,
            passengers_quantity_who_left: Synchronized,
            passengers_quantity_who_left_lock: synchronize.Lock
        ):

        super().__init__()
        self._name = name
        self._opening_doors_at_source_station = opening_doors_at_source_station
        self._train = train
        self._sending_train = sending_train
        self._controller = controller
        self._passengers_boarding_is_over = passengers_boarding_is_over
        self._opening_doors_at_another_station = opening_doors_at_another_station
        self._passengers_quantity_on_train = passengers_quantity_on_train
        self._passengers_quantity_on_train_lock = passengers_quantity_on_train_lock
        self._opening_station = opening_station
        self._passengers_quantity_who_left = passengers_quantity_who_left
        self._passengers_quantity_who_left_lock = passengers_quantity_who_left_lock

    def _pause(self):
        sleep(0.01)

    def _seats_quantity_limit(self):
        return self._passengers_quantity_on_train.value <= SEATS_IN_TRAIN_QUANTITY

    def _operate_value(self, value: Synchronized, value_lock: synchronize.Lock, operation: str):
        method = operations.get(operation)
        with value_lock:
            value.value = getattr(value.value, method)(1)
        self._pause()

    def run(self):
        self._pause()
        came_to_station = self._opening_station.wait(timeout=random()*_WAIT_OPENING_STATION_COEFF)
        self._pause()
        if came_to_station:
            print(f'Пассажир {self._name} пришёл на станцию.')
            ready_to_get_on_train = self._train.acquire(timeout=random()*_WAIT_TRAIN_COEFF)
            self._pause()
            if ready_to_get_on_train:
                waited_boarding_start = self._opening_doors_at_source_station.wait(timeout=random()*_WAIT_OPENING_DOORS_AT_SOURCE_STATION_COEFF)
                self._pause()
                if waited_boarding_start:
                    with self._controller:
                        self._operate_value(self._passengers_quantity_on_train, self._passengers_quantity_on_train_lock, '+')
                        self._operate_value(self._passengers_quantity_who_left, self._passengers_quantity_who_left_lock, '+')
                        self._controller.wait_for(self._seats_quantity_limit)
                        self._pause()
                        print(f'Пассажир {self._name} сел в поезд.')
                    waited_boarding_end = self._passengers_boarding_is_over.wait(timeout=random()*_WAIT_PASSENGERS_BOARDING_IS_OVER_COEFF)
                    self._pause()
                    if waited_boarding_end:
                        self._opening_doors_at_another_station.wait()
                        self._pause()
                        self._operate_value(self._passengers_quantity_on_train, self._passengers_quantity_on_train_lock, '-')
                        self._train.release()
                        self._pause()
                        print(f'Пассажир {self._name} вышел из поезда на другой станции.')
                    else:
                        print(f'(Пассажир {self._name} не смог дождаться окончания посадки на поезд и вышел из поезда)')
                        self._operate_value(self._passengers_quantity_on_train, self._passengers_quantity_on_train_lock, '-')
                else:
                    print(f'(Пассажир {self._name} не смог дождаться открытия дверей поезда и ушёл со станции)')
                    self._operate_value(self._passengers_quantity_who_left, self._passengers_quantity_who_left_lock, '+')
            else:
                print(f'(Пассажир {self._name} не смог дождаться своей посадки на поезд и ушёл со станции)')
                self._operate_value(self._passengers_quantity_who_left, self._passengers_quantity_who_left_lock, '+')
        else:
            print(f'(Пассажир {self._name} не смог дождаться открытия станции и ушёл)')
            self._operate_value(self._passengers_quantity_who_left, self._passengers_quantity_who_left_lock, '+')

PASSENGERS_QUANTITY = 11
SEATS_IN_TRAIN_QUANTITY = 3

opening_doors_at_source_station = Event()
opening_doors_at_another_station = Event()
train = BoundedSemaphore(SEATS_IN_TRAIN_QUANTITY)
sending_train = Event()
controller = Condition()
passengers_boarding_is_over = Event()
opening_station = Event()

passengers_quantity_on_train, passengers_quantity_on_train_lock = Value('i', 0), Lock()
passengers_quantity_who_left, passengers_quantity_who_left_lock = Value('i', 0), Lock()

faker = Faker()
passenger_names = [faker.name() for _ in range(PASSENGERS_QUANTITY)]

passengers = [Passenger(
    name, opening_doors_at_source_station, train,
    sending_train, controller, passengers_boarding_is_over,
    opening_doors_at_another_station, passengers_quantity_on_train, passengers_quantity_on_train_lock,
    opening_station, passengers_quantity_who_left, passengers_quantity_who_left_lock
) for name in passenger_names]

for passenger in passengers:
    passenger.start()

sleep(1)
print('\nСтанция открылась\n')
opening_station.set()
while True:
    if passengers_quantity_who_left.value == PASSENGERS_QUANTITY:
        print('\nНа исходной станции не осталось пассажиров, поезд окончательно остановился.\n')
        break
    sleep(1)
    print('\nДвери поезда на исходной станции открылись.\n')
    opening_doors_at_source_station.set()
    sleep(1)
    print(passengers_quantity_on_train.value, passengers_quantity_who_left.value) #
    passengers_boarding_is_over.set()
    print('\nПосадка пассажиров закончена.')
    sleep(1)
    print(passengers_quantity_on_train.value, passengers_quantity_who_left.value) #
    opening_doors_at_source_station.clear()
    print('Двери поезда на исходной станции закрылись.')
    sleep(1)
    print('Поезд поехал на другую станцию.')
    sleep(3)
    print('Поезд приехал на другую станцию.')
    sleep(1)
    print('Двери поезда на другой станции открылись.\n')
    opening_doors_at_another_station.set()
    sleep(1)
    passengers_boarding_is_over.clear()
    print('\nВысадка пассажиров закончена.')
    sleep(1)
    opening_doors_at_another_station.clear()
    print('Двери поезда на другой станции закрылись.')
    sleep(1)
    print(passengers_quantity_on_train.value, passengers_quantity_who_left.value) #
    print('Поезд поехал на исходную станцию.')
    sleep(3)
    print('Поезд приехал на исходную станцию.')