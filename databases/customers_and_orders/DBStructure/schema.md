# Схема базы данных 1С

## Документы
Документ.CustomerOrders
  Стандартные реквизиты: Ссылка, Номер, Дата, Проведен, ПометкаУдаления
  Реквизиты: customer_id (CustomerId): Справочник.Customers; order_date (OrderDate): Дата; order_status_code (OrderStatusCode): Строка

## Справочники
Справочник.Addresses
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: address_details (AddressDetails): Строка
Справочник.Customers
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: address_id (AddressId): Число; payment_method_code (PaymentMethodCode): Строка; customer_number (CustomerNumber): Строка; customer_name (CustomerName): Строка; customer_address (CustomerAddress): Строка; customer_phone (CustomerPhone): Строка; customer_email (CustomerEmail): Строка
Справочник.OrderItems
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: order_item_id (OrderItemId): Число; order_id (OrderId): Документ.CustomerOrders; product_id (ProductId): Справочник.Products; order_quantity (OrderQuantity): Строка
Справочник.Products
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: product_type_code (ProductTypeCode): Строка; product_name (ProductName): Строка; product_price (ProductPrice): Число