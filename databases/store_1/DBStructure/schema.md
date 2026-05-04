# Схема базы данных 1С

## Справочники
Справочник.Albums
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: id (Id): Число; title (Title): Строка; artist_id (ArtistId): Число
Справочник.Artists
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: name (Name): Строка
Справочник.Customers
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: first_name (FirstName): Строка; last_name (LastName): Строка; company (Company): Строка; address (Address): Строка; city (City): Строка; state (State): Строка; country (Country): Строка; postal_code (PostalCode): Строка; phone (Phone): Строка; fax (Fax): Строка; email (Email): Строка; support_rep_id (SupportRepId): Число
Справочник.Employees
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: last_name (LastName): Строка; first_name (FirstName): Строка; title (Title): Строка; reports_to (ReportsTo): Число; birth_date (BirthDate): Дата; hire_date (HireDate): Дата; address (Address): Строка; city (City): Строка; state (State): Строка; country (Country): Строка; postal_code (PostalCode): Строка; phone (Phone): Строка; fax (Fax): Строка; email (Email): Строка
Справочник.Genres
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: name (Name): Строка
Справочник.InvoiceLines
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: invoice_id (InvoiceId): Число; track_id (TrackId): Число; unit_price (UnitPrice): Число; quantity (Quantity): Число
Справочник.Invoices
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: customer_id (CustomerId): Число; invoice_date (InvoiceDate): Дата; billing_address (BillingAddress): Строка; billing_city (BillingCity): Строка; billing_state (BillingState): Строка; billing_country (BillingCountry): Строка; billing_postal_code (BillingPostalCode): Строка; total (Total): Число
Справочник.Playlists
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: name (Name): Строка
Справочник.PlaylistTracks
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: playlist_id (PlaylistId): Число; track_id (TrackId): Число
Справочник.Tracks
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: name (Name): Строка; album_id (AlbumId): Число; media_type_id (MediaTypeId): Число; genre_id (GenreId): Число; composer (Composer): Строка; milliseconds (Milliseconds): Число; bytes (Bytes): Число; unit_price (UnitPrice): Число

## Перечисления
Перечисление.MediaTypes
  Значения: MPEG_audio_file (MPEG audio file), Protected_AAC_audio_file (Protected AAC audio file), Protected_MPEG_4_video_file (Protected MPEG-4 video file), Purchased_AAC_audio_file (Purchased AAC audio file), AAC_audio_file (AAC audio file)