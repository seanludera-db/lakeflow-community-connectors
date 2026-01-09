# **Smartsheet API Documentation**

## **Authorization**

- **Chosen method**: Personal Access Token (API Access Token) for the Smartsheet REST API 2.0.
- **Base URL**: `https://api.smartsheet.com/2.0`
- **Regional base URLs**:
  - Smartsheet Gov: `https://api.smartsheetgov.com/2.0`
  - Smartsheet Regions Europe: `https://api.smartsheet.eu/2.0`
  - Smartsheet Regions Australia: `https://api.smartsheet.au/2.0`
- **Auth placement**:
  - HTTP header: `Authorization: Bearer <access_token>`
- **Access requirements**:
  - The Smartsheet API is restricted to users on **Business and Enterprise plans**.
  - API tokens can be generated from the Smartsheet UI under Personal Settings → API Access.

**How to generate an access token**:
1. Log in to your Smartsheet account.
2. Click on your account icon in the lower-left corner and select "Personal Settings."
3. Navigate to the "API Access" tab.
4. Click "Generate new access token" and securely store the token (it won't be displayed again).

Example authenticated request:

```bash
curl -X GET \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  "https://api.smartsheet.com/2.0/sheets"
```

**Rate limits**:
- **300 requests per minute** per access token.
- Resource-intensive operations (e.g., attaching a file, retrieving cell history) count as **10 requests** toward this limit.
- Exceeding the rate limit results in HTTP 429 with error code `4003` ("Rate limit exceeded").
- Recommended handling: implement exponential backoff or pause for 60 seconds before retrying.


## **Object List**

For connector purposes, we treat specific Smartsheet REST resources as **objects/tables**.  
The object list is **static** (defined by the connector), not discovered dynamically from an API.

| Object Name | Description | Primary Endpoint | Ingestion Type |
|-------------|-------------|------------------|----------------|
| `sheets` | Sheet metadata including columns, rows, and cells | `GET /sheets/{sheetId}` | `cdc` (upserts based on `modifiedAt`) |

**Connector scope for initial implementation**:
- This documentation focuses on the `sheets` object only.
- Other Smartsheet objects (folders, workspaces, reports, dashboards, users, etc.) are out of scope for initial implementation.

**Notes on sheets**:
- A sheet in Smartsheet is the primary data structure, similar to a spreadsheet.
- Each sheet contains columns (schema definition) and rows (data records).
- Rows contain cells, with each cell corresponding to a column.
- The sheet object can optionally include attachments, discussions, and other metadata when requested.


## **Object Schema**

### General notes

- Smartsheet provides structured JSON responses for sheet objects via its REST API.
- For the connector, we define **tabular schemas** per object, derived from the JSON representation.
- Nested JSON objects (e.g., `columns`, `rows`, `cells`, `source`) are modeled as **nested structures/arrays**.

### `sheets` object (primary table)

**Source endpoints**:
- `GET /sheets` — List all sheets accessible to the user (abbreviated sheet objects).
- `GET /sheets/{sheetId}` — Get detailed sheet including columns, rows, and cells.

**Key behavior**:
- The List Sheets endpoint returns abbreviated sheet metadata without rows/columns.
- The Get Sheet endpoint returns the full sheet including columns, rows, and cell data.
- Supports filtering via query parameters like `include`, `exclude`, `rowsModifiedSince`.

**High-level schema (connector view)**:

Top-level fields from the Smartsheet REST API:

| Column Name | Type | Description |
|-------------|------|-------------|
| `id` | integer (64-bit) | Unique identifier for the sheet. |
| `name` | string | The name of the sheet. |
| `version` | integer | The current version number of the sheet. Incremented on changes. |
| `accessLevel` | string (enum) | User's access level: `OWNER`, `ADMIN`, `EDITOR`, `EDITOR_SHARE`, `VIEWER`, `COMMENTER`. |
| `permalink` | string | A permanent URL that provides direct access to the sheet in Smartsheet. |
| `createdAt` | string (ISO 8601 datetime) | Timestamp when the sheet was created. |
| `modifiedAt` | string (ISO 8601 datetime) | Timestamp when the sheet was last modified. Used as incremental cursor. |
| `ownerId` | integer (64-bit) | Unique identifier of the sheet owner. |
| `owner` | string | Email address of the sheet owner. |
| `totalRowCount` | integer | Total number of rows in the sheet. |
| `effectiveAttachmentOptions` | array\<string\> | Effective attachment options enabled for the sheet. |
| `ganttEnabled` | boolean | Whether Gantt chart view is enabled. |
| `dependenciesEnabled` | boolean | Whether row dependencies are enabled. |
| `resourceManagementEnabled` | boolean | Whether resource management is enabled. |
| `resourceManagementType` | string | Type of resource management (e.g., `RESOURCE_MANAGEMENT`). |
| `cellImageUploadEnabled` | boolean | Whether cell image upload is enabled. |
| `favorite` | boolean | Whether the sheet is marked as a favorite by the user. |
| `showParentRowsForFilters` | boolean | Whether parent rows are shown for filtered views. |
| `hasSummaryFields` | boolean | Whether the sheet has summary fields. |
| `isMultiPicklistEnabled` | boolean | Whether multi-select picklists are enabled. |
| `source` | struct or null | Information about the source of the sheet (if copied/imported). |
| `projectSettings` | struct or null | Project settings if the sheet is a project sheet. |
| `workspace` | struct or null | Workspace information if the sheet belongs to a workspace. |
| `columns` | array\<struct\> | Array of column definitions for the sheet. |
| `rows` | array\<struct\> | Array of row objects containing cell data. |

**Nested `column` struct** (elements of `columns` array):

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (64-bit) | Unique identifier for the column. |
| `index` | integer | Zero-based position of the column in the sheet. |
| `title` | string | The title/name of the column. |
| `type` | string (enum) | Column type: `TEXT_NUMBER`, `DATE`, `DATETIME`, `CHECKBOX`, `PICKLIST`, `CONTACT_LIST`, `MULTI_CONTACT_LIST`, `DURATION`, `PREDECESSOR`, `ABSTRACT_DATETIME`, `MULTI_PICKLIST`. |
| `primary` | boolean | Whether this is the primary column (leftmost column). |
| `width` | integer | Width of the column in pixels. |
| `hidden` | boolean | Whether the column is hidden. |
| `symbol` | string or null | Symbol for the column (e.g., for checkbox columns). |
| `format` | string or null | Format descriptor for the column. |
| `formula` | string or null | Column formula if applicable. |
| `options` | array\<string\> | Options for picklist columns. |
| `validation` | boolean | Whether validation is enabled. |
| `autoNumberFormat` | struct or null | Auto-number format settings. |
| `contactOptions` | array\<struct\> | Contact options for contact list columns. |
| `version` | integer | Column version number. |
| `locked` | boolean | Whether the column is locked. |
| `lockedForUser` | boolean | Whether the column is locked for the current user. |

**Nested `row` struct** (elements of `rows` array):

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (64-bit) | Unique identifier for the row. |
| `rowNumber` | integer | One-based row number in the sheet. |
| `sheetId` | integer (64-bit) | ID of the sheet this row belongs to. |
| `parentId` | integer (64-bit) or null | ID of the parent row if this is a child row. |
| `siblingId` | integer (64-bit) or null | ID of the sibling row. |
| `expanded` | boolean | Whether the row is expanded (for hierarchical sheets). |
| `createdAt` | string (ISO 8601 datetime) | Row creation timestamp. |
| `modifiedAt` | string (ISO 8601 datetime) | Row last modification timestamp. |
| `createdBy` | struct | User who created the row. |
| `modifiedBy` | struct | User who last modified the row. |
| `permalink` | string | Direct link to the row in Smartsheet. |
| `version` | integer | Row version number. |
| `locked` | boolean | Whether the row is locked. |
| `lockedForUser` | boolean | Whether the row is locked for the current user. |
| `inCriticalPath` | boolean | Whether the row is in the critical path (project sheets). |
| `conditionalFormat` | string or null | Conditional formatting applied to the row. |
| `cells` | array\<struct\> | Array of cell objects for this row. |
| `attachments` | array\<struct\> | Attachments on the row (if requested). |
| `discussions` | array\<struct\> | Discussions on the row (if requested). |

**Nested `cell` struct** (elements of `cells` array within a row):

| Field | Type | Description |
|-------|------|-------------|
| `columnId` | integer (64-bit) | ID of the column this cell belongs to. |
| `value` | any | The raw value stored in the cell. Type depends on column type. |
| `displayValue` | string | Formatted display value as shown in the Smartsheet UI. |
| `objectValue` | struct or null | Object value for multi-contact or predecessor cells. |
| `formula` | string or null | Formula used in the cell. |
| `hyperlink` | struct or null | Hyperlink information if the cell contains a link. |
| `image` | struct or null | Image information if the cell contains an image. |
| `linkInFromCell` | struct or null | Cell link information if linked from another cell. |
| `linksOutToCells` | array\<struct\> | Outgoing cell links. |
| `format` | string or null | Cell format descriptor. |
| `conditionalFormat` | string or null | Conditional format applied. |
| `strict` | boolean | Whether strict mode is enabled. |
| `overrideValidation` | boolean | Whether validation is overridden. |

**Nested `source` struct** (if sheet was copied from another):

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (64-bit) | ID of the source sheet. |
| `type` | string | Type of source (e.g., `sheet`). |

**Nested `user` struct** (for `createdBy`, `modifiedBy`):

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer (64-bit) | User ID. |
| `email` | string | User's email address. |
| `name` | string | User's display name. |

**Example request (List Sheets)**:

```bash
curl -X GET \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  "https://api.smartsheet.com/2.0/sheets?pageSize=100"
```

**Example response (List Sheets, abbreviated)**:

```json
{
  "pageNumber": 1,
  "pageSize": 100,
  "totalPages": 1,
  "totalCount": 2,
  "data": [
    {
      "id": 1234567890123456,
      "name": "Project Tracker",
      "accessLevel": "OWNER",
      "permalink": "https://app.smartsheet.com/sheets/abc123",
      "createdAt": "2024-01-15T10:30:00Z",
      "modifiedAt": "2025-01-08T14:22:00Z"
    },
    {
      "id": 2345678901234567,
      "name": "Budget Overview",
      "accessLevel": "EDITOR",
      "permalink": "https://app.smartsheet.com/sheets/def456",
      "createdAt": "2024-06-20T08:00:00Z",
      "modifiedAt": "2025-01-07T16:45:00Z"
    }
  ]
}
```

**Example request (Get Sheet with rows and columns)**:

```bash
curl -X GET \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  "https://api.smartsheet.com/2.0/sheets/1234567890123456"
```

**Example response (Get Sheet, truncated)**:

```json
{
  "id": 1234567890123456,
  "name": "Project Tracker",
  "version": 15,
  "accessLevel": "OWNER",
  "permalink": "https://app.smartsheet.com/sheets/abc123",
  "createdAt": "2024-01-15T10:30:00Z",
  "modifiedAt": "2025-01-08T14:22:00Z",
  "totalRowCount": 25,
  "columns": [
    {
      "id": 1111111111111111,
      "index": 0,
      "title": "Task Name",
      "type": "TEXT_NUMBER",
      "primary": true,
      "width": 200
    },
    {
      "id": 2222222222222222,
      "index": 1,
      "title": "Due Date",
      "type": "DATE",
      "width": 150
    },
    {
      "id": 3333333333333333,
      "index": 2,
      "title": "Status",
      "type": "PICKLIST",
      "width": 100,
      "options": ["Not Started", "In Progress", "Complete"]
    }
  ],
  "rows": [
    {
      "id": 4444444444444444,
      "rowNumber": 1,
      "expanded": true,
      "createdAt": "2024-01-15T10:35:00Z",
      "modifiedAt": "2025-01-05T09:00:00Z",
      "cells": [
        {
          "columnId": 1111111111111111,
          "value": "Design Homepage",
          "displayValue": "Design Homepage"
        },
        {
          "columnId": 2222222222222222,
          "value": "2025-01-15",
          "displayValue": "January 15, 2025"
        },
        {
          "columnId": 3333333333333333,
          "value": "In Progress",
          "displayValue": "In Progress"
        }
      ]
    }
  ]
}
```

> The columns listed above define the **complete connector schema** for the `sheets` table.  
> If additional Smartsheet sheet fields are needed in the future, they must be added as new columns here so the documentation continues to reflect the full table schema.


## **Get Object Primary Keys**

There is no dedicated metadata endpoint to get the primary key for the `sheets` object.  
Instead, the primary key is defined **statically** based on the resource schema.

- **Primary key for `sheets`**: `id`  
  - Type: 64-bit integer  
  - Property: Unique across all sheets in Smartsheet. Globally unique identifier.

The connector will:
- Read the `id` field from each sheet record returned by `GET /sheets` or `GET /sheets/{sheetId}`.
- Use it as the immutable primary key for upserts when ingestion type is `cdc`.

For nested data within sheets:
- **Rows**: Primary key is `id` (row ID), unique within the account.
- **Columns**: Primary key is `id` (column ID), unique within the account.
- **Cells**: Composite key of `(rowId, columnId)`.


## **Object's ingestion type**

Supported ingestion types (framework-level definitions):
- `cdc`: Change data capture; supports upserts incrementally.
- `cdc_with_deletes`: Change data capture with delete synchronization.
- `snapshot`: Full replacement snapshot; no inherent incremental support.
- `append`: Incremental but append-only (no updates/deletes).

Planned ingestion type for the `sheets` object:

| Object | Ingestion Type | Rationale |
|--------|----------------|-----------|
| `sheets` | `cdc` | Sheets have a stable primary key `id` and a `modifiedAt` field that can be used as a cursor for incremental syncs. The API provides `rowsModifiedSince` parameter for row-level incremental reads. Deleted rows are **not** returned by the API's incremental parameters (see Known Quirks). |

For `sheets`:
- **Primary key**: `id`
- **Cursor field**: `modifiedAt`
- **Row-level cursor**: `rowsModifiedSince` query parameter filters rows modified after a given timestamp.
- **Sort order**: Results are returned by modification time; pagination is page-based.
- **Deletes**: Smartsheet API does **not** provide information about deleted rows via the `rowsModifiedSince` parameter. To track deletions, webhooks would be required (out of scope for initial implementation). The connector treats this as `cdc` (upserts only) rather than `cdc_with_deletes`.


## **Read API for Data Retrieval**

### List Sheets endpoint

- **HTTP method**: `GET`
- **Endpoint**: `/sheets`
- **Base URL**: `https://api.smartsheet.com/2.0`

**Key query parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | no | 1 | Page number to return. |
| `pageSize` | integer | no | 100 | Number of results per page (max 100 for most endpoints). |
| `includeAll` | boolean | no | false | If true, returns all results without pagination. **Note**: Deprecated as of Dec 2025; transitioning to token-based pagination. |
| `modifiedSince` | string (ISO 8601 datetime) | no | none | Return sheets modified at or after this time. Used for incremental reads at the sheet level. |
| `include` | string | no | none | Comma-separated list of elements to include (e.g., `sheetVersion`, `source`). |

**Pagination strategy**:
- Smartsheet uses page-based pagination with `page` and `pageSize` parameters.
- Response includes `pageNumber`, `pageSize`, `totalPages`, and `totalCount` metadata.
- The connector should:
  - Request with `pageSize=100` for efficiency.
  - Increment `page` until `pageNumber >= totalPages`.
- **Token-based pagination** (newer approach):
  - Use `paginationType=token` and `maxItems` parameters.
  - Response includes `lastKey` token when more items are available.
  - Pass `lastKey` in subsequent requests to continue.

Example listing sheets with pagination:

```bash
curl -X GET \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.smartsheet.com/2.0/sheets?pageSize=100&page=1"
```

### Get Sheet endpoint

- **HTTP method**: `GET`
- **Endpoint**: `/sheets/{sheetId}`

**Path parameters**:
- `sheetId` (integer, required): The unique identifier of the sheet.

**Key query parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include` | string | no | none | Comma-separated list: `attachments`, `discussions`, `format`, `filters`, `filterDefinitions`, `ownerInfo`, `source`, `summary`, `ganttConfig`, `objectValue`, `rowPermalink`, `rowWriterInfo`, `columnType`, `writerInfo`. |
| `exclude` | string | no | none | Comma-separated list of elements to exclude: `filteredOutRows`, `linkInFromCellDetails`, `linksOutToCellsDetails`, `nonexistentCells`. |
| `rowsModifiedSince` | string (ISO 8601 datetime) | no | none | Return only rows modified since this timestamp. Used for incremental row-level reads. |
| `rowIds` | string | no | none | Comma-separated list of row IDs to include. |
| `columnIds` | string | no | none | Comma-separated list of column IDs to include. |
| `rowNumbers` | string | no | none | Comma-separated list of row numbers to include. |
| `filterId` | integer | no | none | Apply a filter to the results. |
| `level` | integer | no | 1 | Specifies the level of detail: 0 (no nested objects), 1 (include basic), 2 (include multi-contact details). |
| `page` | integer | no | 1 | Page number for paginated row results. |
| `pageSize` | integer | no | 100 | Number of rows per page. |

**Incremental strategy**:

1. **Initial full load**:
   - Request `GET /sheets/{sheetId}` without `rowsModifiedSince`.
   - Paginate through all rows using `page` and `pageSize`.
   - Record the sheet's `modifiedAt` timestamp.

2. **Incremental sync**:
   - Use `rowsModifiedSince` parameter with the last sync timestamp (minus a small lookback window, e.g., 1-5 minutes for safety).
   - Only rows added or updated since that time are returned.
   - **Important**: Deleted rows are NOT returned by this parameter.

Example incremental read:

```bash
SINCE_TS="2025-01-01T00:00:00Z"
curl -X GET \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://api.smartsheet.com/2.0/sheets/1234567890123456?rowsModifiedSince=${SINCE_TS}"
```

**Handling deletes**:
- The Smartsheet API does **not** provide deleted row information via `rowsModifiedSince`.
- To detect deletes, options include:
  - Periodic full snapshot comparison (compare current row IDs with previous).
  - Webhooks (out of scope for initial connector).
- For the initial connector, deletes are not tracked (`cdc` mode, not `cdc_with_deletes`).


## **Field Type Mapping**

### Column type to data type mapping

| Smartsheet Column Type | Example Values | Connector Logical Type | Notes |
|------------------------|----------------|------------------------|-------|
| `TEXT_NUMBER` | `"Hello"`, `123.45` | string or number | Can contain text or numbers; treat as string for safety. |
| `DATE` | `"2025-01-15"` | date | ISO 8601 date format. |
| `DATETIME` | `"2025-01-15T10:30:00Z"` | timestamp | Full timestamp with timezone. |
| `CHECKBOX` | `true`, `false` | boolean | Binary checkbox state. |
| `PICKLIST` | `"In Progress"` | string | Single selection from predefined options. |
| `MULTI_PICKLIST` | `["Option1", "Option2"]` | array\<string\> | Multiple selections from predefined options. |
| `CONTACT_LIST` | `{"email": "user@example.com"}` | struct | Single contact reference. |
| `MULTI_CONTACT_LIST` | `[{"email": "a@ex.com"}, {"email": "b@ex.com"}]` | array\<struct\> | Multiple contact references. |
| `DURATION` | `"5d"` | string | Duration for project management (days, hours). |
| `PREDECESSOR` | `[{"rowId": 123, "type": "FS"}]` | array\<struct\> | Task dependencies. |
| `ABSTRACT_DATETIME` | varies | string | Abstract datetime representation. |

### General type mapping (Smartsheet JSON → connector logical types)

| JSON Type | Example Fields | Connector Logical Type | Notes |
|-----------|----------------|------------------------|-------|
| integer (64-bit) | `id`, `sheetId`, `rowId`, `columnId`, `ownerId` | `long` | Use 64-bit integer to avoid overflow. |
| string | `name`, `title`, `permalink`, `value`, `displayValue` | string | UTF-8 text. |
| boolean | `primary`, `locked`, `expanded`, `favorite` | boolean | Standard true/false. |
| string (ISO 8601 datetime) | `createdAt`, `modifiedAt` | timestamp with timezone | Stored as UTC timestamps. |
| object | `source`, `workspace`, `projectSettings`, `hyperlink` | struct | Nested records. |
| array | `columns`, `rows`, `cells`, `options` | array\<struct\> or array\<string\> | Arrays of objects or primitives. |
| nullable fields | `parentId`, `formula`, `source` | corresponding type + null | Missing fields should surface as `null`. |

### Special behaviors

- Cell `value` field type varies based on column type; connector may need to inspect `columnType` for proper parsing.
- `displayValue` is always a string representation suitable for display.
- Timestamps use ISO 8601 format in UTC (e.g., `"2025-01-15T10:30:00Z"`).
- IDs are 64-bit integers and should not be truncated.


## **Known Quirks & Edge Cases**

- **Deleted rows not in incremental sync**:
  - The `rowsModifiedSince` parameter does NOT return information about deleted rows.
  - Webhooks can notify of row deletions but only provide `rowId`, not the deleted data.
  - For full delete tracking, periodic snapshot comparison or webhooks would be required.

- **Rate limits**:
  - 300 requests per minute per access token.
  - Some operations count as 10 requests (e.g., file attachments, cell history).
  - Implement exponential backoff for 429 errors.

- **Plan restrictions**:
  - The Smartsheet API is only available on Business and Enterprise plans.
  - Free or Pro plan users cannot access the API.

- **Regional endpoints**:
  - Users in different regions (Gov, EU, AU) must use the appropriate regional base URL.
  - Connector configuration should support specifying the region.

- **Pagination deprecation**:
  - As of December 2025, `includeAll`, `page`, `pageSize`, and related response properties are deprecated for some endpoints (e.g., `GET /sights`).
  - Transitioning to token-based pagination using `lastKey`.
  - The `GET /sheets` endpoint still supports page-based pagination as of this writing.

- **Cell value types**:
  - The `value` field in cells can be different types (string, number, boolean, object) depending on the column type.
  - The connector should use `displayValue` for consistent string representation or handle type coercion.

- **Large sheets**:
  - Sheets with many rows should be paginated using `page` and `pageSize` in the Get Sheet request.
  - Consider using `rowIds` or `columnIds` to limit returned data.


## **Research Log**

| Source Type | URL | Accessed (UTC) | Confidence | What it confirmed |
|-------------|-----|----------------|------------|-------------------|
| Official Docs | https://developers.smartsheet.com/api/smartsheet/introduction | 2025-01-09 | High | Base URLs, API access restrictions, authentication overview. |
| Official Docs | https://developers.smartsheet.com/api/smartsheet/guides/basics/authentication | 2025-01-09 | High | Bearer token authentication, how to generate access tokens. |
| Official Docs | https://developers.smartsheet.com/api/smartsheet/guides/basics/pagination | 2025-01-09 | High | Page-based and token-based pagination details. |
| Official Docs | https://developers.smartsheet.com/api/smartsheet/openapi/sheets | 2025-01-09 | High | Sheet schema, endpoints, query parameters. |
| Official Docs | https://developers.smartsheet.com/api/smartsheet/changelog | 2025-01-09 | High | Pagination deprecation notices, API updates. |
| Web Search | https://www.postman.com/api-reference-library/smartsheet | 2025-01-09 | High | List Sheets and Get Sheet response schema fields. |
| Web Search | https://www.simworkflow.com/integration-operation/smartsheet-sheets-sheetid-get-6d1 | 2025-01-09 | Medium | Get Sheet response structure with columns, rows, cells. |
| Community | https://community.smartsheet.com/discussion/115262 | 2025-01-09 | High | Confirmed `rowsModifiedSince` does not return deleted row information. |
| Web Search | https://stackoverflow.com/questions/64334700 | 2025-01-09 | Medium | Webhooks for delete tracking only provide rowId, not data. |
| Web Search | https://smartsheet-platform.github.io/smartsheet-csharp-sdk | 2025-01-09 | High | Column types: TEXT_NUMBER, DATE, CHECKBOX, PICKLIST, CONTACT_LIST. |
| Web Search | https://help.knoema.com/hc/en-us/articles/15728185477012 | 2025-01-09 | Medium | Airbyte Smartsheet connector behavior - one sheet per connector instance. |
| Official Docs | https://www.smartsheet.com/content-center/best-practices/tips-tricks/api-best-practices | 2025-01-09 | High | Rate limits (300/min), exponential backoff recommendations. |


## **Sources and References**

- **Official Smartsheet API documentation** (highest confidence)
  - `https://developers.smartsheet.com/api/smartsheet/introduction`
  - `https://developers.smartsheet.com/api/smartsheet/guides/basics/authentication`
  - `https://developers.smartsheet.com/api/smartsheet/guides/basics/pagination`
  - `https://developers.smartsheet.com/api/smartsheet/openapi/sheets`
  - `https://developers.smartsheet.com/api/smartsheet/changelog`
  - `https://www.smartsheet.com/content-center/best-practices/tips-tricks/api-best-practices`

- **Postman API Reference** (high confidence)
  - `https://www.postman.com/api-reference-library/smartsheet`

- **Airbyte Smartsheet connector** (medium confidence)
  - `https://pypi.org/project/airbyte-source-smartsheets/`
  - `https://help.knoema.com/hc/en-us/articles/15728185477012-Smartsheets-Source-Connector-Documentation`

- **Smartsheet Community** (high confidence for edge cases)
  - `https://community.smartsheet.com/discussion/115262` (deleted rows not in rowsModifiedSince)

When conflicts arise, **official Smartsheet documentation** is treated as the source of truth.
