import time
from typing import Dict, List, Iterator

import requests
from pyspark.sql.types import (
    StructType,
    StructField,
    LongType,
    StringType,
    BooleanType,
    ArrayType,
)


class LakeflowConnect:
    """Smartsheet connector for ingesting sheet data into Databricks."""

    # Default base URL for Smartsheet API
    DEFAULT_BASE_URL = "https://api.smartsheet.com/2.0"

    # Regional base URLs
    REGIONAL_URLS = {
        "default": "https://api.smartsheet.com/2.0",
        "gov": "https://api.smartsheetgov.com/2.0",
        "eu": "https://api.smartsheet.eu/2.0",
        "au": "https://api.smartsheet.au/2.0",
    }

    # Rate limit: 300 requests per minute
    MAX_RETRIES = 3
    RETRY_WAIT_SECONDS = 60

    def __init__(self, options: Dict[str, str]) -> None:
        """
        Initialize the Smartsheet connector.

        Args:
            options: A dictionary containing:
                - access_token (required): Smartsheet API access token
                - region (optional): One of 'default', 'gov', 'eu', 'au'
                - base_url (optional): Custom base URL (overrides region)
        """
        if "access_token" not in options:
            raise ValueError("access_token is required in options")

        self.access_token = options["access_token"]

        # Determine base URL from region or custom URL
        if "base_url" in options:
            self.base_url = options["base_url"].rstrip("/")
        elif "region" in options:
            region = options["region"].lower()
            if region not in self.REGIONAL_URLS:
                raise ValueError(
                    f"Invalid region '{region}'. Must be one of: {list(self.REGIONAL_URLS.keys())}"
                )
            self.base_url = self.REGIONAL_URLS[region]
        else:
            self.base_url = self.DEFAULT_BASE_URL

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # Supported tables
        self._tables = ["sheets"]

    def list_tables(self) -> List[str]:
        """
        List names of all tables supported by the Smartsheet connector.

        Returns:
            A list of table names.
        """
        return self._tables

    def get_table_schema(
        self, table_name: str, table_options: Dict[str, str]
    ) -> StructType:
        """
        Fetch the schema of a table.

        Args:
            table_name: The name of the table to fetch the schema for.
            table_options: A dictionary of options for accessing the table.

        Returns:
            A StructType object representing the schema of the table.
        """
        if table_name not in self._tables:
            raise ValueError(f"Table '{table_name}' is not supported.")

        if table_name == "sheets":
            return self._get_sheets_schema()

        raise ValueError(f"Table '{table_name}' is not supported.")

    def _get_sheets_schema(self) -> StructType:
        """Define the schema for the sheets table."""
        # User struct for createdBy/modifiedBy
        user_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("email", StringType(), True),
                StructField("name", StringType(), True),
            ]
        )

        # Source struct
        source_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("type", StringType(), True),
            ]
        )

        # Workspace struct
        workspace_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("name", StringType(), True),
            ]
        )

        # Auto-number format struct
        auto_number_format_struct = StructType(
            [
                StructField("prefix", StringType(), True),
                StructField("suffix", StringType(), True),
                StructField("fill", StringType(), True),
                StructField("startingNumber", LongType(), True),
            ]
        )

        # Contact option struct
        contact_option_struct = StructType(
            [
                StructField("email", StringType(), True),
                StructField("name", StringType(), True),
            ]
        )

        # Column struct
        column_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("index", LongType(), True),
                StructField("title", StringType(), True),
                StructField("type", StringType(), True),
                StructField("primary", BooleanType(), True),
                StructField("width", LongType(), True),
                StructField("hidden", BooleanType(), True),
                StructField("symbol", StringType(), True),
                StructField("format", StringType(), True),
                StructField("formula", StringType(), True),
                StructField("options", ArrayType(StringType()), True),
                StructField("validation", BooleanType(), True),
                StructField("autoNumberFormat", auto_number_format_struct, True),
                StructField(
                    "contactOptions", ArrayType(contact_option_struct), True
                ),
                StructField("version", LongType(), True),
                StructField("locked", BooleanType(), True),
                StructField("lockedForUser", BooleanType(), True),
            ]
        )

        # Hyperlink struct (for cells)
        hyperlink_struct = StructType(
            [
                StructField("url", StringType(), True),
                StructField("sheetId", LongType(), True),
                StructField("reportId", LongType(), True),
                StructField("sightId", LongType(), True),
            ]
        )

        # Image struct (for cells)
        image_struct = StructType(
            [
                StructField("id", StringType(), True),
                StructField("height", LongType(), True),
                StructField("width", LongType(), True),
                StructField("altText", StringType(), True),
            ]
        )

        # Link in from cell struct
        link_in_from_cell_struct = StructType(
            [
                StructField("sheetId", LongType(), True),
                StructField("sheetName", StringType(), True),
                StructField("columnId", LongType(), True),
                StructField("rowId", LongType(), True),
                StructField("status", StringType(), True),
            ]
        )

        # Cell struct
        cell_struct = StructType(
            [
                StructField("columnId", LongType(), True),
                StructField("value", StringType(), True),  # Stored as string for flexibility
                StructField("displayValue", StringType(), True),
                StructField("objectValue", StringType(), True),  # JSON string for complex objects
                StructField("formula", StringType(), True),
                StructField("hyperlink", hyperlink_struct, True),
                StructField("image", image_struct, True),
                StructField("linkInFromCell", link_in_from_cell_struct, True),
                StructField("linksOutToCells", ArrayType(link_in_from_cell_struct), True),
                StructField("format", StringType(), True),
                StructField("conditionalFormat", StringType(), True),
                StructField("strict", BooleanType(), True),
                StructField("overrideValidation", BooleanType(), True),
            ]
        )

        # Attachment struct
        attachment_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("name", StringType(), True),
                StructField("attachmentType", StringType(), True),
                StructField("mimeType", StringType(), True),
                StructField("sizeInKb", LongType(), True),
                StructField("parentId", LongType(), True),
                StructField("parentType", StringType(), True),
                StructField("createdAt", StringType(), True),
                StructField("createdBy", user_struct, True),
            ]
        )

        # Discussion struct
        discussion_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("title", StringType(), True),
                StructField("parentId", LongType(), True),
                StructField("parentType", StringType(), True),
                StructField("lastCommentedAt", StringType(), True),
                StructField("createdBy", user_struct, True),
            ]
        )

        # Row struct
        row_struct = StructType(
            [
                StructField("id", LongType(), True),
                StructField("rowNumber", LongType(), True),
                StructField("sheetId", LongType(), True),
                StructField("parentId", LongType(), True),
                StructField("siblingId", LongType(), True),
                StructField("expanded", BooleanType(), True),
                StructField("createdAt", StringType(), True),
                StructField("modifiedAt", StringType(), True),
                StructField("createdBy", user_struct, True),
                StructField("modifiedBy", user_struct, True),
                StructField("permalink", StringType(), True),
                StructField("version", LongType(), True),
                StructField("locked", BooleanType(), True),
                StructField("lockedForUser", BooleanType(), True),
                StructField("inCriticalPath", BooleanType(), True),
                StructField("conditionalFormat", StringType(), True),
                StructField("cells", ArrayType(cell_struct), True),
                StructField("attachments", ArrayType(attachment_struct), True),
                StructField("discussions", ArrayType(discussion_struct), True),
            ]
        )

        # Project settings struct
        project_settings_struct = StructType(
            [
                StructField("workingDays", ArrayType(StringType()), True),
                StructField("nonWorkingDays", ArrayType(StringType()), True),
                StructField("lengthOfDay", LongType(), True),
            ]
        )

        # Main sheets schema
        return StructType(
            [
                StructField("id", LongType(), False),
                StructField("name", StringType(), True),
                StructField("version", LongType(), True),
                StructField("accessLevel", StringType(), True),
                StructField("permalink", StringType(), True),
                StructField("createdAt", StringType(), True),
                StructField("modifiedAt", StringType(), True),
                StructField("ownerId", LongType(), True),
                StructField("owner", StringType(), True),
                StructField("totalRowCount", LongType(), True),
                StructField("effectiveAttachmentOptions", ArrayType(StringType()), True),
                StructField("ganttEnabled", BooleanType(), True),
                StructField("dependenciesEnabled", BooleanType(), True),
                StructField("resourceManagementEnabled", BooleanType(), True),
                StructField("resourceManagementType", StringType(), True),
                StructField("cellImageUploadEnabled", BooleanType(), True),
                StructField("favorite", BooleanType(), True),
                StructField("showParentRowsForFilters", BooleanType(), True),
                StructField("hasSummaryFields", BooleanType(), True),
                StructField("isMultiPicklistEnabled", BooleanType(), True),
                StructField("source", source_struct, True),
                StructField("projectSettings", project_settings_struct, True),
                StructField("workspace", workspace_struct, True),
                StructField("columns", ArrayType(column_struct), True),
                StructField("rows", ArrayType(row_struct), True),
            ]
        )

    def read_table_metadata(
        self, table_name: str, table_options: Dict[str, str]
    ) -> Dict:
        """
        Fetch the metadata of a table.

        Args:
            table_name: The name of the table to fetch the metadata for.
            table_options: A dictionary of options for accessing the table.

        Returns:
            A dictionary containing the metadata of the table.
        """
        if table_name not in self._tables:
            raise ValueError(f"Table '{table_name}' is not supported.")

        metadata = {
            "sheets": {
                "primary_keys": ["id"],
                "cursor_field": "modifiedAt",
                "ingestion_type": "cdc",
            },
        }

        return metadata[table_name]

    def read_table(
        self, table_name: str, start_offset: dict, table_options: Dict[str, str]
    ) -> (Iterator[dict], dict):
        """
        Read the records of a table and return an iterator of records and an offset.

        Args:
            table_name: The name of the table to read.
            start_offset: The offset to start reading from.
            table_options: A dictionary of options for accessing the table.
                - include_attachments: If "true", include attachments in the response.
                - include_discussions: If "true", include discussions in the response.
                - expand_rows: If "true", fetch full sheet details including rows.
                  Default is "true". Set to "false" for metadata-only.

        Returns:
            An iterator of records in JSON format and an offset.
        """
        if table_name not in self._tables:
            raise ValueError(f"Table '{table_name}' is not supported.")

        if table_name == "sheets":
            return self._read_sheets(start_offset, table_options)

        raise ValueError(f"Table '{table_name}' is not supported.")

    def _make_request(self, url: str, params: dict = None) -> dict:
        """
        Make a GET request to the Smartsheet API with retry logic for rate limits.

        Args:
            url: The URL to request.
            params: Optional query parameters.

        Returns:
            The JSON response as a dictionary.
        """
        for attempt in range(self.MAX_RETRIES):
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit exceeded - wait and retry
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_WAIT_SECONDS)
                    continue
                else:
                    raise Exception(
                        f"Smartsheet API rate limit exceeded after {self.MAX_RETRIES} retries"
                    )
            else:
                raise Exception(
                    f"Smartsheet API error: {response.status_code} - {response.text}"
                )

        raise Exception("Unexpected error in _make_request")

    def _list_sheets(self, modified_since: str = None) -> Iterator[dict]:
        """
        List all sheets accessible to the user with pagination.

        Args:
            modified_since: ISO 8601 timestamp to filter sheets modified after this time.

        Yields:
            Sheet metadata dictionaries.
        """
        page = 1
        page_size = 100

        while True:
            params = {"page": page, "pageSize": page_size}
            if modified_since:
                params["modifiedSince"] = modified_since

            url = f"{self.base_url}/sheets"
            data = self._make_request(url, params)

            sheets = data.get("data", [])
            for sheet in sheets:
                yield sheet

            # Check if we've reached the last page
            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break

            page += 1

    def _get_sheet_details(
        self, sheet_id: int, rows_modified_since: str = None, table_options: dict = None
    ) -> dict:
        """
        Get detailed sheet information including columns, rows, and cells.

        Args:
            sheet_id: The ID of the sheet to fetch.
            rows_modified_since: ISO 8601 timestamp to filter rows modified after this time.
            table_options: Options for the request.

        Returns:
            Full sheet data including columns and rows.
        """
        url = f"{self.base_url}/sheets/{sheet_id}"
        params = {}

        if rows_modified_since:
            params["rowsModifiedSince"] = rows_modified_since

        # Build include parameter based on table options
        include_parts = []
        if table_options:
            if table_options.get("include_attachments", "").lower() == "true":
                include_parts.append("attachments")
            if table_options.get("include_discussions", "").lower() == "true":
                include_parts.append("discussions")

        if include_parts:
            params["include"] = ",".join(include_parts)

        return self._make_request(url, params)

    def _convert_cell_value_to_string(self, value) -> str:
        """Convert cell value to string for consistent storage."""
        if value is None:
            return None
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def _process_cell(self, cell: dict) -> dict:
        """Process a cell to normalize its value field to string."""
        processed = dict(cell)
        if "value" in processed:
            processed["value"] = self._convert_cell_value_to_string(processed["value"])
        if "objectValue" in processed and processed["objectValue"] is not None:
            import json
            if isinstance(processed["objectValue"], dict):
                processed["objectValue"] = json.dumps(processed["objectValue"])
            else:
                processed["objectValue"] = str(processed["objectValue"])
        return processed

    def _process_row(self, row: dict) -> dict:
        """Process a row to normalize cell values."""
        processed = dict(row)
        if "cells" in processed and processed["cells"]:
            processed["cells"] = [self._process_cell(cell) for cell in processed["cells"]]
        return processed

    def _process_sheet(self, sheet: dict) -> dict:
        """Process a sheet to normalize all nested data."""
        processed = dict(sheet)
        if "rows" in processed and processed["rows"]:
            processed["rows"] = [self._process_row(row) for row in processed["rows"]]
        return processed

    def _read_sheets(
        self, start_offset: dict, table_options: Dict[str, str]
    ) -> (Iterator[dict], dict):
        """
        Read sheets with incremental support.

        Args:
            start_offset: The offset to start reading from.
                - modified_since: ISO 8601 timestamp for incremental reads.
            table_options: Options for the request.

        Returns:
            An iterator of sheet records and the next offset.
        """
        modified_since = None
        if start_offset:
            modified_since = start_offset.get("modified_since")

        # Determine if we should expand rows (default: true)
        expand_rows = table_options.get("expand_rows", "true").lower() != "false"

        # Track the latest modification time for the next offset
        latest_modified_at = modified_since

        def generate_records():
            nonlocal latest_modified_at

            # List all sheets (with optional modified_since filter)
            for sheet_meta in self._list_sheets(modified_since):
                sheet_id = sheet_meta["id"]
                sheet_modified_at = sheet_meta.get("modifiedAt")

                # Update latest_modified_at for the next offset
                if sheet_modified_at:
                    if latest_modified_at is None or sheet_modified_at > latest_modified_at:
                        latest_modified_at = sheet_modified_at

                if expand_rows:
                    # Fetch full sheet details including rows
                    # For incremental reads, we could use rowsModifiedSince, but since
                    # we're returning the entire sheet object, we fetch all rows.
                    sheet_data = self._get_sheet_details(
                        sheet_id, 
                        rows_modified_since=None,  # Get all rows for each sheet
                        table_options=table_options
                    )
                    yield self._process_sheet(sheet_data)
                else:
                    # Return only sheet metadata without rows
                    yield sheet_meta

        # Create the iterator
        records = list(generate_records())

        # Build the next offset
        next_offset = {"modified_since": latest_modified_at} if latest_modified_at else {}

        return iter(records), next_offset

