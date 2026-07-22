# Data Areas

- `input/sampe_2` contains immutable copies of the three supplied Sample 2 JSON files.
- `canonical` is reserved for normalized Parquet tables produced by ingestion.

Generated canonical data should not be edited manually. Each output should retain
its cycle ID, source checksum, extraction time, schema version, and configuration
version.
