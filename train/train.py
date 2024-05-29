from multiprocessing import Process, Event, Condition, BoundedSemaphore, Lock, synchronize
from multiprocessing import Value
from multiprocessing.sharedctypes import Synchronized
from time import sleep
from faker import Faker


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
        self._opening_station.wait()
        self._pause()
        print(f'Пассажир {self._name} пришёл на станцию')
        self._train.acquire()
        self._pause()
        self._opening_doors_at_source_station.wait()
        self._pause()
        with self._controller:
            self._operate_value(self._passengers_quantity_on_train, self._passengers_quantity_on_train_lock, '+')
            self._operate_value(self._passengers_quantity_who_left, self._passengers_quantity_who_left_lock, '+')
            self._controller.wait_for(self._seats_quantity_limit)
            self._pause()
            print(f'Пассажир {self._name} сел в поезд')
        self._passengers_boarding_is_over.wait()
        self._pause()
        self._opening_doors_at_another_station.wait()
        self._pause()
        self._operate_value(self._passengers_quantity_on_train, self._passengers_quantity_on_train_lock, '-')
        self._train.release()
        print(f'Пассажир {self._name} вышел из поезда')

PASSENGERS_QUANTITY = 5
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
    passengers_boarding_is_over.set()
    print('\nПосадка пассажиров закончена.')
    sleep(1)
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
    print('Поезд поехал на исходную станцию.')
    sleep(3)
    print('Поезд приехал на исходную станцию.')