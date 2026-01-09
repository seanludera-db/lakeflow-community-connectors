# Lakeflow Smartsheet Community Connector

This documentation provides setup instructions and reference information for the Smartsheet source connector.

## Prerequisites

- A Smartsheet account on a **Business or Enterprise plan** (API access is not available on Free or Pro plans)
- A Smartsheet API access token with permissions to read sheets

## Setup

### Required Connection Parameters

To configure the connector, provide the following parameters in your connector options:

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `access_token` | string | Yes | Smartsheet API access token for authentication | `ll4ir5shd3...` |
| `region` | string | No | Smartsheet region. One of: `default`, `gov`, `eu`, `au`. Defaults to `default` if not specified. | `eu` |
| `base_url` | string | No | Custom base URL (overrides `region` if provided) | `https://api.smartsheet.com/2.0` |

**Table-Specific Options:**

This connector supports per-table options. Include the following in `externalOptionsAllowList`: `include_attachments,include_discussions,expand_rows`

| Option | Type | Description |
|--------|------|-------------|
| `include_attachments` | string | Set to `"true"` to include attachments in the sheet response |
| `include_discussions` | string | Set to `"true"` to include discussions in the sheet response |
| `expand_rows` | string | Set to `"true"` (default) to include full sheet details with rows, or `"false"` to retrieve metadata only |

### How to Generate an Access Token

1. Log in to your Smartsheet account.
2. Click on your account icon in the lower-left corner and select **Personal Settings**.
3. Navigate to the **API Access** tab.
4. Click **Generate new access token** and securely store the token (it won't be displayed again).

### Regional Endpoints

Smartsheet offers regional deployments. Use the appropriate `region` value based on your account:

| Region | Value | Base URL |
|--------|-------|----------|
| Default (US) | `default` | `https://api.smartsheet.com/2.0` |
| Government | `gov` | `https://api.smartsheetgov.com/2.0` |
| Europe | `eu` | `https://api.smartsheet.eu/2.0` |
| Australia | `au` | `https://api.smartsheet.au/2.0` |

### Create a Unity Catalog Connection

A Unity Catalog connection for this connector can be created in two ways via the UI:
1. Follow the Lakeflow Community Connector UI flow from the "Add Data" page
2. Select any existing Lakeflow Community Connector connection for this source or create a new one
3. Set the `externalOptionsAllowList` to: `include_attachments,include_discussions,expand_rows`

The connection can also be created using the standard Unity Catalog API.


## Supported Objects

The Smartsheet connector supports the following object:

| Object Name | Description | Primary Key | Cursor Field | Ingestion Type |
|-------------|-------------|-------------|--------------|----------------|
| `sheets` | Smartsheet sheets including columns, rows, and cells | `id` | `modifiedAt` | `cdc` (upserts) |

### `sheets` Object Details

The `sheets` object represents complete Smartsheet spreadsheets, including:

- **Sheet metadata**: name, access level, permalink, timestamps, owner information
- **Columns**: Schema definition with column types, options, and formatting
- **Rows**: Data records containing cells with values, formulas, and formatting
- **Optional inclusions**: Attachments and discussions when configured

**Incremental Sync Behavior:**
- Uses the `modifiedAt` timestamp to track changes at the sheet level
- Sheets modified since the last sync are re-fetched with their complete data
- **Note**: Deleted sheets are not tracked in incremental mode. If full delete detection is required, periodic snapshot comparisons may be necessary.

**Configuration Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `include_attachments` | `"false"` | Include attachment metadata for sheets and rows |
| `include_discussions` | `"false"` | Include discussion/comment metadata for sheets and rows |
| `expand_rows` | `"true"` | Fetch full sheet details including all rows and cells |


## Data Type Mapping

The following table shows how Smartsheet data types are mapped to Databricks types:

| Smartsheet Type | Databricks Type | Notes |
|-----------------|-----------------|-------|
| Integer (64-bit) | `LONG` | Used for IDs (`id`, `sheetId`, `rowId`, `columnId`) |
| String | `STRING` | Text values, names, permalinks |
| Boolean | `BOOLEAN` | Checkbox values, flags |
| ISO 8601 DateTime | `STRING` | Timestamps stored as ISO 8601 strings (e.g., `createdAt`, `modifiedAt`) |
| Nested Object | `STRUCT` | Complex objects like `source`, `workspace`, `createdBy` |
| Array | `ARRAY<STRUCT>` or `ARRAY<STRING>` | Lists of columns, rows, cells, or string options |

### Cell Value Handling

Cell values in Smartsheet can be of various types depending on the column type. The connector normalizes all cell values to strings for consistent storage:

| Column Type | Example Value | Storage Format |
|-------------|---------------|----------------|
| `TEXT_NUMBER` | `"Hello"` or `123.45` | Stored as string |
| `DATE` | `"2025-01-15"` | ISO 8601 date string |
| `DATETIME` | `"2025-01-15T10:30:00Z"` | ISO 8601 timestamp string |
| `CHECKBOX` | `true` / `false` | `"true"` or `"false"` |
| `PICKLIST` | `"In Progress"` | String value |
| `MULTI_PICKLIST` | Multiple selections | Stored in `objectValue` as JSON |
| `CONTACT_LIST` | Contact reference | Stored in `objectValue` as JSON |


## How to Run

### Step 1: Clone/Copy the Source Connector Code
Follow the Lakeflow Community Connector UI, which will guide you through setting up a pipeline using the selected source connector code.

### Step 2: Configure Your Pipeline

1. Update the `pipeline_spec` in the main pipeline file (e.g., `ingest.py`).
2. Configure table-specific options to control data retrieval:

```json
{
  "pipeline_spec": {
    "connection_name": "your_smartsheet_connection",
    "object": [
      {
        "table": {
          "source_table": "sheets",
          "include_attachments": "true",
          "include_discussions": "false",
          "expand_rows": "true"
        }
      }
    ]
  }
}
```

3. (Optional) Customize the source connector code if needed for special use cases.

### Step 3: Run and Schedule the Pipeline

#### Best Practices

- **Start Small**: Begin by syncing sheets without attachments/discussions to verify connectivity
- **Use Incremental Sync**: The connector uses `modifiedAt` timestamps to only fetch changed sheets
- **Set Appropriate Schedules**: Balance data freshness requirements with API usage limits
- **Mind the Rate Limits**: Smartsheet allows 300 API requests per minute per access token. The connector implements automatic retry with backoff for rate limit errors.

#### Troubleshooting

**Common Issues:**

| Issue | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Invalid or expired access token | Generate a new access token from Smartsheet Personal Settings |
| `429 Rate limit exceeded` | Too many API requests | The connector automatically retries with 60-second delays. Consider reducing sync frequency. |
| `403 Forbidden` | Insufficient permissions or wrong plan | Verify you have a Business or Enterprise plan and proper sheet access |
| Missing sheet data | Account doesn't have access to sheets | Verify the access token owner has appropriate sharing permissions |
| Wrong region | Using default region for non-US account | Set the correct `region` parameter (`gov`, `eu`, or `au`) |


## References

- [Smartsheet API Introduction](https://developers.smartsheet.com/api/smartsheet/introduction)
- [Smartsheet API Authentication](https://developers.smartsheet.com/api/smartsheet/guides/basics/authentication)
- [Smartsheet API Best Practices](https://www.smartsheet.com/content-center/best-practices/tips-tricks/api-best-practices)
- [Smartsheet API Sheets Reference](https://developers.smartsheet.com/api/smartsheet/openapi/sheets)

