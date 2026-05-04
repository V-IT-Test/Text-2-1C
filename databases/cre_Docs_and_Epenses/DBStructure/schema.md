# Схема базы данных 1С

## Документы
Документ.Documents
  Стандартные реквизиты: Ссылка, Номер, Дата, Проведен, ПометкаУдаления
  Реквизиты: Document_Type_Code (DocumentTypeCode): Справочник.RefDocumentTypes; Project_ID (ProjectId): Справочник.Projects; Document_Date (DocumentDate): Дата; Document_Name (DocumentName): Строка; Document_Description (DocumentDescription): Строка; Other_Details (OtherDetails): Строка

## Справочники
Справочник.Accounts
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Statement_ID (StatementId): Справочник.Statements; Account_Details (AccountDetails): Строка
Справочник.Projects
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Project_Details (ProjectDetails): Строка
Справочник.RefBudgetCodes
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Budget_Type_Description (BudgetTypeDescription): Строка
Справочник.RefDocumentTypes
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Document_Type_Name (DocumentTypeName): Строка; Document_Type_Description (DocumentTypeDescription): Строка
Справочник.Statements
  Стандартные реквизиты: Ссылка, Код, Наименование, ПометкаУдаления
  Реквизиты: Statement_Details (StatementDetails): Строка

## Регистры сведений
РегистрСведений.DocumentsWithExpenses
  Измерения: Document_ID (DocumentId): Документ.Documents; Budget_Type_Code (BudgetTypeCode): Справочник.RefBudgetCodes
  Ресурсы: Document_Details (DocumentDetails): Строка