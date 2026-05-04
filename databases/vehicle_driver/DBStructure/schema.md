# Схема базы данных 1С

## Справочники
Справочник.Driver
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Citizenship: Строка; Racing_Series (RacingSeries): Строка
Справочник.Vehicle
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Model: Строка; Build_Year (BuildYear): Строка; Top_Speed (TopSpeed): Число; Power: Число; Builder: Строка; Total_Production (TotalProduction): Строка

## Регистры сведений
РегистрСведений.VehicleDriver
  Измерения: Driver_ID (DriverId): Справочник.Driver; Vehicle_ID (VehicleId): Справочник.Vehicle