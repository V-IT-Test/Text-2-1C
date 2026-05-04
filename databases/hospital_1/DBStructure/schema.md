# Схема базы данных 1С

## Документы
Документ.Appointment
  Стандартные реквизиты: Ссылка, Номер, Дата, Проведен, ПометкаУдаления
  Реквизиты: Patient: Справочник.Patient; PrepNurse (Prepnurse): Справочник.Nurse; Physician: Справочник.Physician; Start: Дата; End: Дата; ExaminationRoom (Examinationroom): Строка
Документ.Stay
  Стандартные реквизиты: Ссылка, Номер, Дата, Проведен, ПометкаУдаления
  Реквизиты: Patient: Справочник.Patient; Room: Справочник.Room; StayStart (Staystart): Дата; StayEnd (Stayend): Дата

## Справочники
Справочник.Block
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
Справочник.Department
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Head: Справочник.Physician
Справочник.Medication
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Brand: Строка; Description_Attr (Описание): Строка
Справочник.Nurse
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Position: Строка; Registered: Булево; SSN (Ssn): Число
Справочник.Patient
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Address: Строка; Phone: Строка; InsuranceID (Insuranceid): Число; PCP (Pcp): Справочник.Physician
Справочник.Physician
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Position: Строка; SSN (Ssn): Число
Справочник.Procedures
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Name (Наименование): Строка; Cost: Число
Справочник.Room
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: RoomType (Roomtype): Строка; BlockFloor (Blockfloor): Справочник.Block; BlockCode (Blockcode): Справочник.Block; Unavailable: Булево

## Регистры сведений
РегистрСведений.AffiliatedWith
  Измерения: Physician: Справочник.Physician; Department: Справочник.Department
  Ресурсы: PrimaryAffiliation (Primaryaffiliation): Булево
РегистрСведений.OnCall
  Измерения: Nurse: Справочник.Nurse; BlockFloor (Blockfloor): Справочник.Block; BlockCode (Blockcode): Справочник.Block
РегистрСведений.Prescribes
  Измерения: Physician: Справочник.Physician; Patient: Справочник.Patient; Medication: Справочник.Medication; Appointment: Документ.Appointment
  Ресурсы: Dose: Строка
РегистрСведений.TrainedIn
  Измерения: Physician: Справочник.Physician; Treatment: Справочник.Procedures
  Ресурсы: CertificationDate (Certificationdate): Дата; CertificationExpires (Certificationexpires): Дата
РегистрСведений.Undergoes
  Измерения: Patient: Справочник.Patient; Procedures: Справочник.Procedures; Stay: Документ.Stay; Physician: Справочник.Physician; AssistingNurse (Assistingnurse): Справочник.Nurse