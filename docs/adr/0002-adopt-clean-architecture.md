# ADR 0002: Adopt Clean Architecture and IStorage Interfaces

## Status
Accepted

## Context
The previous monolithic design where the UI directly communicated with the database layer made the codebase difficult to test and fragile. Swapping the storage backend (e.g., from JSON to SQLite) required changes across dozens of UI files.

## Decision
We will strictly follow **Clean Architecture** principles:
1.  **Domain Layer**: Pure business logic and models (`Note`, `Folder`) with no knowledge of UI or DB.
2.  **Infrastructure Layer**: Implements concrete storage (`StorageManager`) but only via the `IStorage` interface.
3.  **UI Layer**: Communicates with the `NoteService` (Domain) which then uses the `IStorage` interface.

All data passing through the system will transition from raw dictionaries to type-safe **Domain Models**.

## Consequences
- **Positive**: Allows switching database backends (e.g., to PostgreSQL or Cloud Storage) without changing any UI or business logic code.
- **Positive**: Enables robust Unit Testing of business logic by mocking the `IStorage` interface.
- **Positive**: Improved IDE support (IntelliSense) due to type-safe models.
- **Neutral**: Requires more boilerplate (Interfaces + Models) than simple scripts.
