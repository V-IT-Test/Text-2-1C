# Схема базы данных 1С

## Справочники
Справочник.AnalyticalLayer
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Customers_and_Services_ID (CustomersAndServicesId): Число; Pattern_Recognition (PatternRecognition): Строка; Analytical_Layer_Type_Code (AnalyticalLayerTypeCode): Строка
Справочник.Channels
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Channel_Details (ChannelDetails): Строка
Справочник.CustomerInteractions
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Channel_ID (ChannelId): Справочник.Channels; Customer_ID (CustomerId): Справочник.Customers; Service_ID (ServiceId): Справочник.Services; Status_Code (StatusCode): Строка; Services_and_Channels_Details (ServicesAndChannelsDetails): Строка
Справочник.Customers
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Customer_Details (CustomerDetails): Строка
Справочник.IntegrationPlatform
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Customer_Interaction_ID (CustomerInteractionId): Справочник.CustomerInteractions; Integration_Platform_Details (IntegrationPlatformDetails): Строка
Справочник.Services
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Service_Details (ServiceDetails): Строка

## Регистры сведений
РегистрСведений.CustomersAndServices
  Измерения: Customer_ID (CustomerId): Справочник.Customers; Service_ID (ServiceId): Справочник.Services
  Ресурсы: Customers_and_Services_Details (CustomersAndServicesDetails): Строка