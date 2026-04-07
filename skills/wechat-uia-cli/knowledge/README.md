# Knowledge Files

`customer-followup` can optionally evaluate chip selection and similar project cases.

It looks for these files in `--knowledge-dir`:

- `chip_catalog.json`
- `project_cases.json`

If they are not provided, the skill falls back to the bundled virtual files in this folder:

- `chip_catalog.virtual.json`
- `project_cases.virtual.json`

The bundled data is intentionally fictional and only demonstrates the schema.
Replace it with real internal资料后，第二层“选型校验 / 相似案例”能力才会更可靠。
