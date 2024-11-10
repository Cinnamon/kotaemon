# Troubleshooting Guide

## Common Issues

### File Processing
- If a file is only used once for DB population (#476), check the file monitoring settings
- For files that work inconsistently (#447), verify:
  1. File format compatibility
  2. Character encoding
  3. File size limits

### GraphRAG
- If NanoGraphRAG fails with KeyError (#451), verify graph configuration
- For graph writing issues (#449), check permissions and storage paths
- When using external MILVUS DB (#438):
  1. Verify connection settings
  2. Check authentication
  3. Confirm schema compatibility

### Document Handling
- For table splitting issues (#466), consider:
  1. Using table-aware chunking
  2. Adjusting chunk size
  3. Implementing custom table handlers

### UI/UX
- If highlights aren't visible in reference docs (#469), verify:
  1. PDF.js setup
  2. Browser compatibility
  3. Citation format 